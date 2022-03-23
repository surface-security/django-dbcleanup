from django.apps import AppConfig
from django.conf import settings

APP_SETTINGS = {
    # "app.model", "days_of_history_to_keep", "reference_datetime_field"
    'HISTORY_MODELS': None,
    # tables that do not map to any model but should not be deleted
    'REQUIRED_TABLES': set(),
}


class DBCleanupConfig(AppConfig):
    name = 'dbcleanup'
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        super().ready()
        for k, v in APP_SETTINGS.items():
            _k = f'{self.name.upper()}_{k}'
            if not hasattr(settings, _k):
                setattr(settings, _k, v)
