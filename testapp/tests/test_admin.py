from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse


class Test(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('tester', 'tester@test.it', 'tester')

    def test_changelist(self):
        """
        test to make sure that every DB engine allows to *at least* list tables
        """
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

        r = self.client.get(reverse('admin:dbcleanup_table_changelist'))
        self.assertEqual(r.status_code, 200)
