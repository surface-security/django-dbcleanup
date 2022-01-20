from django.db import models
from django.apps import registry
from functools import lru_cache


@lru_cache()
def model_tables():
    from .models import Table

    tables_in_use = {}
    for m in registry.apps.get_models():
        if m == Table:
            # skip ourselves
            continue
        if not m._meta.managed:
            # skip models not managed by django
            continue
        tables_in_use[m._meta.db_table] = m
        for f in m._meta.get_fields(include_parents=False):
            if isinstance(f, models.ManyToManyField):
                tables_in_use[f.m2m_db_table()] = m
    return tables_in_use
