from django.contrib import admin
from django.contrib.admin.filters import SimpleListFilter
from django.db.models import query
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html

from . import models, utils


def human_size(attribute, column_title=None):
    if column_title is None:
        f = models.Table._meta.get_field(attribute)
        column_title = f.verbose_name

    def _get_it(obj):
        val = getattr(obj, attribute)
        return format_html(
            '<span data-toggle="tooltip" data-placement="bottom" title={}>{}</span>',
            val,
            filesizeformat(val),
        )

    _get_it.short_description = column_title
    _get_it.admin_order_field = attribute
    return _get_it


class TableAppFilter(SimpleListFilter):
    title = 'App'
    parameter_name = 'app_label'

    def lookups(self, request, model_admin):
        unique_labels = {x._meta.app_label for x in utils.model_tables().values()}
        return [(x, x) for x in unique_labels]

    def queryset(self, request, queryset):
        val = self.value()
        if val is None:
            return None
        app_tables = [k for k, v in utils.model_tables().items() if v._meta.app_label == val]
        return queryset.filter(name__in=app_tables)


class TableModelFilter(SimpleListFilter):
    title = 'Model'
    parameter_name = 'label'

    def lookups(self, request, model_admin):
        unique_labels = {x._meta.label for x in utils.model_tables().values()}
        return [(x, x) for x in unique_labels]

    def queryset(self, request, queryset):
        val = self.value()
        if val is None:
            return None
        app_tables = [k for k, v in utils.model_tables().items() if v._meta.label == val]
        return queryset.filter(name__in=app_tables)


@admin.register(models.Table)
class TableAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'get_app',
        'get_model',
        human_size('size', 'size'),
        'rows',
        # need to specify custom title because these are not fields in PostgreSQL table model
        human_size('avg_row_length', 'average row length'),
        human_size('data_length', 'data length'),
        human_size('index_length', 'index length'),
    )
    search_fields = ('name',)
    list_filter = (TableAppFilter, TableModelFilter)

    def get_ordering(self, request):
        # cannot use class "ordering" attribute as it asserts "size" is not a field...
        return ('-size', 'name')

    def get_app(self, obj):
        if obj.name in utils.model_tables():
            return utils.model_tables()[obj.name]._meta.app_label

    get_app.short_description = 'App'

    def get_model(self, obj):
        if obj.name in utils.model_tables():
            return utils.model_tables()[obj.name]._meta.verbose_name

    get_model.short_description = 'Model'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
