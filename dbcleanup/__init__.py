__version__ = '0.1.5'

# set default_app_config when using django earlier than 3.2
try:
    import django

    if django.VERSION < (3, 2):
        default_app_config = 'dbcleanup.apps.DBCleanupConfig'
except ImportError:
    pass
