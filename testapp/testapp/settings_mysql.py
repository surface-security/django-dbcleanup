from .settings import *  # noqa
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'mysql',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': os.getenv('DBCLEANUP_TEST_MYSQL_HOST', '127.0.0.1'),
        'PORT': os.getenv('DBCLEANUP_TEST_MYSQL_PORT', '8877'),
        'TEST': {'CHARSET': 'utf8mb4', 'COLLATION': 'utf8mb4_bin'},
    }
}
