from io import StringIO

from django.test import TestCase
from django.core.management import call_command
from django.db.migrations.recorder import MigrationRecorder


class Test(TestCase):
    def test_command(self):
        out = StringIO()
        call_command('dbcleanup', stdout=out, just='migrations')
        # there might be old tables in the testdb, do not assume empty output...
        baseline = {x.split(' ')[1] for x in out.getvalue().splitlines()}
        m = MigrationRecorder.Migration.objects.create(app='random_name_120397129837', name='0001_initial')
        call_command('dbcleanup', stdout=out, just='migrations')
        new_output = {x.split(' ')[1] for x in out.getvalue().splitlines()}
        self.assertEqual(
            new_output - baseline,
            {'random_name_120397129837'},
        )
        # still exists
        try:
            m.refresh_from_db()
        except MigrationRecorder.Migration.DoesNotExist:
            self.fail('migration should have not been deleted')
        call_command('dbcleanup', stdout=out, just='migrations', force=True)
        # now gone
        try:
            m.refresh_from_db()
            self.fail('migration should have been deleted')
        except MigrationRecorder.Migration.DoesNotExist:
            pass
