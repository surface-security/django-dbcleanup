# django-dbcleanup

Easily monitor database usage - and clean it up (based on your django models)

This pluggable app provides:
* visibility over database disk space usage for your models
* command to remove unused tables and recover disk space
* remove historical data from models that have *any* `DateTimeField` (configurable in the project settings.py)

## Usage

### model and admin view
`dbcleanup.Table` is an unmanaged model mapped to information tables in MySQL and PostgreSQL and added to django admin

![image](https://user-images.githubusercontent.com/63779195/145431955-e20f4a16-924e-4159-8b63-8853ef66f8aa.png)

### command

`dbcleanup` is the management command that can be used (or scheduled) to remove unused
```
$ ./manage.py dbcleanup -h
usage: manage.py dbcleanup [-h] [-f] [-i] [-j {tables,history,analyze,migrations}] [--no-fk] [--version] [-v {0,1,2,3}] [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback] [--no-color]
                           [--force-color] [--skip-checks]

Remove database tables that do not map to any models, such as when a django app is removed/disabled.

optional arguments:
  -h, --help            show this help message and exit
  -f, --force           Delete the items (instead of just listing them)
  -i, --interactive     Ask which items to delete, interactively
  -j {tables,history,analyze,migrations}, --just {tables,history,analyze,migrations}
                        Perform only a subset of actions
  --no-fk               Disable FOREIGNKEY_CHECK when DROPping tables - CAREFUL! use only if you are sure the constraints are not from a table in use (ie: circular dependencies between drop candidates)
```

Need to use `--force` or `--interactive` to actually perform changes, otherwise it'll be a dry run.  
Covered actions are:
* `tables`: remove database tables that do not map to any model (ie: when a app is removed from the project, there is no migration to delete the tables) - use `settings.DBCLEANUP_REQUIRED_TABLES` to whitelist tables that would otherwise be removed
* `history`: remove old records for the models defined in `settings.DBCLEANUP_HISTORY_MODELS` (more below)
* `analyze`: only for MySQL - force analyze on all the tables to update the row count and size estimates
* `migrations`: remove migrations (from `django_migrations` table) that not in the project migration path (ie: after migration squashing and reset)

### historical data

`settings.DBCLEANUP_HISTORY_MODELS` is a list of tuples where each tuple is `(MODEL_NAME, DAYS_TO_KEEP, DATE_TIME_FIELD_NAME)`.

```
# someproject/settings.py
DBCLEANUP_HISTORY_MODELS = [
    ('notifications.notification', 365, 'time'),
    ...
]
```

With this setup, when `./manage.py dbcleanup -j history` is executed, all `notifications.Notification` entries with `time` older than 365 days would be deleted.  
History cleanup is skipped if it would cascade into other models (unless it's a multi-table model and it would cascade to the parent model).
