import unittest
from unittest import mock
from io import StringIO

from django.test import TestCase
from django.apps import registry
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.conf import settings

from dbcleanup import utils, models, admin


@unittest.skipUnless(
    settings.DATABASES['default']['ENGINE'] in ('django.db.backends.mysql', 'django.db.backends.postgresql_psycopg2'),
    "only mysql and postgresql",
)
class Test(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = get_user_model().objects.create_user(
            'tester', 'tester@ppb.it', 'tester', is_staff=True, is_superuser=True
        )
        # make sure cache is always cleared for tests
        utils.model_tables.cache_clear()

    def _login(self):
        self.assertTrue(self.client.login(username='tester', password='tester'))

    def test_table_list(self):
        self.assertEqual(
            sorted(models.Table.objects.values_list('name', flat=True)),
            [
                'auth_group',
                'auth_group_permissions',
                'auth_permission',
                'auth_user',
                'auth_user_groups',
                'auth_user_user_permissions',
                'django_admin_log',
                'django_content_type',
                'django_migrations',
                'django_session',
                'testapp_bread',
                'testapp_food',
                'testapp_food_notes',
                'testapp_foodmonster',
                'testapp_note',
            ],
        )

    def test_m2m_table_model(self):
        """
        test to make sure that an M2M table is mapped in a model relation is mapped to its definition, not to the children models
        ie: testapp_food_notes (Food.notes) should always be mapped to Food, not to Bread
        """
        ta = admin.TableAdmin(models.Table, None)
        self.assertEqual(
            ta.get_model(models.Table.objects.get(name='testapp_food_notes')),
            'food',
        )

    def test_view(self):
        r = self.client.get(reverse('admin:dbcleanup_table_changelist'))
        self.assertEqual(r.status_code, 302)
        self._login()
        # use q= to make sure the table shows in the first page...!
        r = self.client.get(reverse('admin:dbcleanup_table_changelist') + '?q=auth_user')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'>auth_user<', r.content)

    def test_command(self):
        out = StringIO()
        call_command('dbcleanup', stdout=out, just='tables')
        # there might be old tables in the testdb, do not assume empty output...
        baseline = {x.split(' ')[1] for x in out.getvalue().splitlines()}
        # cannot create tables inside TransactionTests (it's mysql), so let's "remove" a model
        org_list = [m for m in registry.apps.get_models() if m._meta.db_table != 'auth_user']
        utils.model_tables.cache_clear()
        with mock.patch('django.apps.registry.apps.get_models', return_value=org_list):
            call_command('dbcleanup', stdout=out, just='tables')
            self.assertEqual(
                {x.split(' ')[1] for x in out.getvalue().splitlines()} - baseline,
                {'auth_user', 'auth_user_groups', 'auth_user_user_permissions'},
            )
