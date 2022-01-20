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
    settings.DATABASES['default']['ENGINE'] in ('django.db.backends.mysql'),
    "only mysql",
)
class Test(TestCase):
    def test_command(self):
        out = StringIO()
        call_command('dbcleanup', stdout=out, just='analyze')
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
