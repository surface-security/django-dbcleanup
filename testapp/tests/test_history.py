from io import StringIO
from django.utils import timezone
from django.test import TestCase, override_settings
from django.core.management import call_command, CommandError


from testapp.models import Note, Bread, FoodMonster


class Test(TestCase):
    @override_settings(DBCLEANUP_HISTORY_MODELS=[('testapp.note', 365, 'time')])
    def test_delete_by_date(self):
        Note.objects.create(
            message='Too old, delete me',
            time=timezone.now() - timezone.timedelta(days=390),
        )
        Note.objects.create(
            message='Keep me',
            time=timezone.now(),
        )

        out = StringIO()
        err = StringIO()
        call_command('dbcleanup', just='history', stdout=out, stderr=err)
        # not deleted
        self.assertEqual(Note.objects.count(), 2)
        self.assertEqual(
            out.getvalue(),
            '''\
testapp.Note cleanup would delete:
 - testapp.Note: 1
''',
        )
        self.assertEqual(err.getvalue(), '')

        out = StringIO()
        err = StringIO()
        call_command('dbcleanup', just='history', force=True, stdout=out, stderr=err)
        # actually deleted
        self.assertEqual(Note.objects.count(), 1)
        self.assertEqual(
            out.getvalue(),
            '''\
testapp.Note cleanup deleted:
 - testapp.Note: 1
''',
        )
        self.assertEqual(err.getvalue(), '')

    @override_settings(
        # test tuple input as well
        DBCLEANUP_HISTORY_MODELS=[(('testapp', 'bread'), 10, 'last_eaten')]
    )
    def test_delete_by_date_cascade(self):
        bread = Bread.objects.create(last_eaten=timezone.now() - timezone.timedelta(days=20))
        monster = FoodMonster.objects.create(food=bread)

        out = StringIO()
        err = StringIO()
        with self.assertRaises(CommandError):
            call_command('dbcleanup', just='history', force=True, stdout=out, stderr=err)

        self.assertEqual(out.getvalue(), '')
        # testapp.Food is not reported because cascading to parent models is allowed (and required)
        self.assertEqual(
            err.getvalue(),
            '''\
testapp.Bread cleanup aborted as it would cascade to:
 - testapp.FoodMonster: 1
''',
        )
        self.assertEqual(Bread.objects.count(), 1)
        self.assertEqual(FoodMonster.objects.count(), 1)

        # once cascade is deleted by itself
        monster.delete()

        # bread can be cleaned up
        out = StringIO()
        err = StringIO()
        call_command('dbcleanup', just='history', force=True, stdout=out, stderr=err)
        self.assertEqual(err.getvalue(), '')
        self.assertEqual(Bread.objects.count(), 0)

    @override_settings(DBCLEANUP_HISTORY_MODELS=[(('testapp', 'bread'), 10, 'last_eaten')])
    def test_delete_m2m_cascade(self):
        note = Note.objects.create(message='random', time=timezone.now())
        bread = Bread.objects.create(last_eaten=timezone.now() - timezone.timedelta(days=20))
        bread.notes.add(note)

        out = StringIO()
        err = StringIO()
        call_command('dbcleanup', just='history', stdout=out, stderr=err)

        self.assertEqual(err.getvalue(), '')
        self.assertEqual(
            out.getvalue(),
            '''\
testapp.Bread cleanup would delete:
 - testapp.Food_notes: 1
 - testapp.Bread: 1
 - testapp.Food: 1
''',
        )
        self.assertEqual(Bread.objects.count(), 1)
        self.assertEqual(Note.objects.count(), 1)

        # bread can be cleaned up
        out = StringIO()
        err = StringIO()
        call_command('dbcleanup', just='history', force=True, stdout=out, stderr=err)
        self.assertEqual(err.getvalue(), '')
        self.assertEqual(Bread.objects.count(), 0)
        # note wasn't deleted, only the M2M entry!
        self.assertEqual(Note.objects.count(), 1)
