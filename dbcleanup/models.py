from django.db import models
from django.db.models.expressions import RawSQL
from django.conf import settings


def _choose_model():
    # would this be cleaner in a
    if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':

        class TableManager(models.Manager):
            def get_queryset(self):
                return (
                    super()
                    .get_queryset()
                    .filter(schema=RawSQL('DATABASE()', []))
                    .annotate(size=RawSQL('data_length + index_length', []))
                )

        class MySQLTable(models.Model):
            objects = TableManager()
            all_tables = models.Manager()

            # FIXME: no key as this is a mysql view... how to tell django to see CONCAT(name + schema) as primary_key?
            # just table_name for now though that is definitely not true...
            name = models.CharField(max_length=64, primary_key=True, db_column='table_name')
            schema = models.CharField(max_length=64, db_column='table_schema')

            rows = models.PositiveBigIntegerField(null=True, db_column='table_rows')
            avg_row_length = models.PositiveBigIntegerField(null=True, verbose_name='Average row length')
            data_length = models.PositiveBigIntegerField(null=True)
            max_data_length = models.PositiveBigIntegerField(null=True, verbose_name='Maximum data length')
            index_length = models.PositiveBigIntegerField(null=True)

            class Meta:
                managed = False
                db_table = 'information_schema`.`TABLES'

            def __str__(self) -> str:
                return f'{self.schema}.{self.name}'

        return MySQLTable

    if settings.DATABASES['default']['ENGINE'] in (
        'django.db.backends.postgresql_psycopg2',
        'django.db.backends.postgresql',
    ):
        """
        based on https://wiki.postgresql.org/wiki/Disk_Usage

        ```
            SELECT c.oid,nspname AS table_schema,relname AS table_name
                , c.reltuples AS row_estimate
                , pg_total_relation_size(c.oid) AS total_bytes
                , pg_indexes_size(c.oid) AS index_bytes
                , pg_total_relation_size(reltoastrelid) AS toast_bytes
            FROM pg_class c
            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE relkind = 'r' and nspname = 'public';
        ```
        """

        class TableManager(models.Manager):
            def get_queryset(self):
                return (
                    super()
                    .get_queryset()
                    .annotate(
                        size=RawSQL('pg_total_relation_size(pg_class.oid)', []),
                        # pg_column_size does not seem to be the same...
                        avg_row_length=RawSQL('NULL', []),
                        data_length=RawSQL('pg_relation_size(pg_class.oid)', []),
                        # PG equivalent for this...? any use for it anyway?
                        max_data_length=RawSQL('NULL', []),
                        index_length=RawSQL('pg_indexes_size(pg_class.oid)', []),
                    )
                    .filter(schema__nspname='public', relkind='r')
                )

        class PGNameSpace(models.Model):
            oid = models.IntegerField(primary_key=True)
            nspname = models.CharField(max_length=255, null=True)

            class Meta:
                managed = False
                db_table = 'pg_namespace'

            def __str__(self) -> str:
                return f'{self.schema}.{self.name}'

        class PGTable(models.Model):
            objects = TableManager()
            all_tables = models.Manager()

            name = models.CharField(max_length=64, primary_key=True, db_column='relname')
            schema = models.ForeignKey(PGNameSpace, db_column='relnamespace', on_delete=models.CASCADE)
            relkind = models.CharField(max_length=255, null=True)

            rows = models.PositiveBigIntegerField(null=True, db_column='reltuples')

            class Meta:
                managed = False
                db_table = 'pg_class'

            def __str__(self) -> str:
                return f'{self.schema}.{self.name}'

        return PGTable

    class TableManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().none()

    class NoTable(models.Model):
        """
        bogus to allow projects to run with unsupported DB engines
        (but without any functionality from this app)
        """

        objects = TableManager()

        name = models.CharField(max_length=64, primary_key=True)
        rows = models.PositiveBigIntegerField(null=True)
        size = models.IntegerField(default=0)

        class Meta:
            managed = False

    return NoTable


class Table(_choose_model()):
    class Meta:
        proxy = True
