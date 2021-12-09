from django.core.management import CommandError, BaseCommand
from django.conf import settings
from django.db import connection, transaction
from django.db.models import ManyToManyField
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db.migrations.loader import MigrationLoader

from dbcleanup import utils, models

REQUIRED_TABLES = {'django_migrations'}


class Command(BaseCommand):
    help = 'Remove database tables that do not map to any models, such as when a django app is removed/disabled.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-f', '--force', action='store_true', help='Delete the items (instead of just listing them)'
        )
        parser.add_argument('-i', '--interactive', action='store_true', help='Ask which items to delete, interactively')
        parser.add_argument(
            '-j',
            '--just',
            action='append',
            choices=('tables', 'history', 'analyze', 'migrations'),
            help='Perform only a subset of actions',
        )
        parser.add_argument(
            '--no-fk',
            action='store_true',
            help='Disable FOREIGNKEY_CHECK when DROPping tables - CAREFUL! use only if you are sure the constraints are not from a table in use (ie: circular dependencies between drop candidates)',
        )

    def _clean_tables(self, options):
        """
        Find tables in database that do not map to a model (and drop them)
        :param options:
        :return:
        """
        if settings.DATABASES['default']['ENGINE'] not in (
            'django.db.backends.mysql',
            'django.db.backends.postgresql_psycopg2',
        ):
            raise CommandError('this is only for mysql and postgresql')
        self._handle_tables(options)

    @staticmethod
    def _analyze_tables(tables=None):
        """
        MySQL stores approximate data (table size and row count) in INFORMATION_SCHEMA.
        If it's MyISAM it is only updated after ANALYZE or OPTIMIZE is executed on the table.
        If it's InnoDB and `innodb_stats_persistent` is enabled, it's updated automatically but it does not consider
        schema changes such as new indexes. So even then, ANALYZE needs to be executed after schema changes.
        This run ANALYZE on all the tables.
        :param options:
        :return:
        """
        if settings.DATABASES['default']['ENGINE'] not in ('django.db.backends.mysql',):
            raise CommandError('this is only for mysql')
        if tables is None:
            tables_in_use = set(utils.model_tables())
            tables_in_use.update(settings.DBCLEANUP_REQUIRED_TABLES)
            tables_in_use.update(REQUIRED_TABLES)
        else:
            tables_in_use = set(tables)
        with connection.cursor() as cursor:
            for table in tables_in_use:
                cursor.execute(f'ANALYZE TABLE {table}')  # nosec: table comes from settings.py or model tables

    @staticmethod
    def _delete_intention(model, query, commit=False, allow_cascade=None):
        """
        TODO allow_cascade...
        even any deletions start being blocked by this and we want to allow cascade,
        consider doing it on an entry basis (add bool to each entry in HISTORY_TABLES setting)
        or an array/set of the allowed cascades (in app.Model format)
        """
        # allow cascading to parent models (otherwise children can never be deleted...)
        _allow = {x._meta.label for x in query.model._meta.parents.keys()}
        # allow cascading to M2M intermediary models
        _allow.update(
            {
                f.remote_field.through._meta.label
                for f in query.model._meta.get_fields()
                if isinstance(f, ManyToManyField)
            }
        )
        # allow itself to be deleted, ofc!
        _allow.add(query.model._meta.label)
        # append the custom ones, if any
        if allow_cascade:
            _allow.update(allow_cascade)

        with transaction.atomic():
            deleted, rows_deleted = query.delete()
            rows_blocked = {k: v for k, v in rows_deleted.items() if k not in _allow and v > 0}
            if rows_blocked:
                raise CascadeException(model, deleted, rows_blocked)
            transaction.set_rollback(not commit)
        return deleted, rows_deleted

    def _model_tuple(self, model):
        if isinstance(model, str):
            return model.split('.')
        return model

    def _clean_history_intention(self, model, q, options):
        if options['force']:
            return self._delete_intention(model, q, True)

        deleted, rows_deleted = self._delete_intention(model, q)
        if deleted and options['interactive']:
            self.stdout.write(f'{model} cleanup will delete:\n')
            for k, v in rows_deleted.items():
                if v:
                    self.stdout.write(f' - {k}: {v}\n')
            ans = input('Delete? (y/N) ')  # nosec - surface is py3-only, input() is safe
            if ans.lower().strip() == 'y':
                deleted, rows_deleted = self._delete_intention(model, q, True)
            else:
                deleted = 0
        return deleted, rows_deleted

    def _clean_history_print(self, items, err=False):
        st = self.stderr if err else self.stdout
        for k, v in items:
            if v:
                st.write(f' - {k}: {v}\n')

    def _clean_history(self, options):
        _exit = 0
        for model, log_size, field in settings.DBCLEANUP_HISTORY_MODELS:
            model_tuple = self._model_tuple(model)
            if len(model_tuple) != 2:
                self.stderr.write(f'{model} is not a valid, it should be a string with app_label.model or a tuple')
                continue

            ct = ContentType.objects.get_by_natural_key(*model_tuple)
            # normalize model name to match against .delete() return labels (and for capitalized printing!)
            model = ct.model_class()._meta.label
            q = ct.get_all_objects_for_this_type(**{f'{field}__lt': timezone.now() - timezone.timedelta(days=log_size)})

            try:
                deleted, rows_deleted = self._clean_history_intention(model, q, options)
            except CascadeException as e:
                _exit = 1
                self.stderr.write(f'{model} cleanup aborted as it would cascade to:\n')
                self._clean_history_print(e.args[2].items(), err=True)
                continue

            if deleted:
                if options['force'] or options['interactive']:
                    self.stdout.write(f'{model} cleanup deleted:\n')
                else:
                    self.stdout.write(f'{model} cleanup would delete:\n')
                self._clean_history_print(rows_deleted.items())
        return _exit

    def _drop_table(self, table_name, no_fk_check=False):
        try:
            with connection.cursor() as cursor:
                if no_fk_check:
                    cursor.execute(f'SET FOREIGN_KEY_CHECKS=0')
                cursor.execute(f'DROP TABLE {table_name}')  # nosec - no sqli, not user input
            self.stdout.write(f'Dropped {table_name}')
        except Exception as e:
            self.stderr.write(
                f'Failed to drop {table_name}: {e} - if DB constraints, maybe running again after will work'
            )
        finally:
            if no_fk_check:
                # reset FK CHECK to 1 in case this connection remains in use (ie: used somewhere else than a command)
                with connection.cursor() as cursor:
                    cursor.execute(f'SET FOREIGN_KEY_CHECKS=1')

    def _handle_tables(self, options):
        tables_in_use = set(utils.model_tables())
        tables_in_use.update(settings.DBCLEANUP_REQUIRED_TABLES)
        tables_in_use.update(REQUIRED_TABLES)

        for table in models.Table.objects.exclude(name__in=tables_in_use):
            self.stdout.write(f'- {table.name} ({table.size})\n')
            if options['force']:
                self._drop_table(table.name, options['no_fk'])
            elif options['interactive']:
                ans = input('Drop it? (y/N) ')  # nosec - surface is py3-only, input() is safe
                if ans.lower().strip() == 'y':
                    self._drop_table(table.name, options['no_fk'])

    def _clean_migrations(self, options):
        # list migrations based on showmigrations command
        loader = MigrationLoader(connection, ignore_no_migrations=False)
        migrated_apps = {l for l in loader.migrated_apps}

        to_delete = {}
        for m, v in loader.applied_migrations.items():
            if m[0] not in migrated_apps:
                if m[0] not in to_delete:
                    to_delete[m[0]] = []
                to_delete[m[0]].append(v)

        for app, migs in to_delete.items():
            self.stdout.write(f'- {app} ({len(migs)})\n')
            if options['force']:
                self._drop_migrations(migs)
            elif options['interactive']:
                ans = input('Drop it? (y/N) ')  # nosec - surface is py3-only, input() is safe
                if ans.lower().strip() == 'y':
                    self._drop_migrations(migs)

    def _drop_migrations(self, migs):
        for mig in migs:
            try:
                mig.delete()
                self.stdout.write(f'Dropped {mig}')
            except Exception as e:
                self.stderr.write(f'Failed to drop {mig}: {e}')

    def _opt(self, opt, options):
        if not options['just'] or opt in options['just']:
            return True
        return False

    def handle(self, *args, **options):
        if self._opt('tables', options):
            self._clean_tables(options)
        if self._opt('migrations', options):
            self._clean_migrations(options)
        if self._opt('history', options) and self._clean_history(options) != 0:
            raise CommandError('some errors, please review')
        if self._opt('analyze', options):
            self._analyze_tables()


class CascadeException(Exception):
    """error thrown when deletion cascades to unallowed models"""
