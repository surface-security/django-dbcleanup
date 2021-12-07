from .settings import *  # noqa
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': os.getenv('DBCLEANUP_TEST_MYSQL_HOST', '127.0.0.1'),
        'PORT': os.getenv('DBCLEANUP_TEST_MYSQL_PORT', '8878'),
    }
}
