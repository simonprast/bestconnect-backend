from django.contrib import admin
from .models import MailModel


class MailAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'to_email',
        'date',
        'from_email'
    )

    list_filter = (
        'from_email',
    )

    search_fields = (
        'to_email',
        'date',
        'from_email',
        'message'
    )

    readonly_fields = ('date', 'user', 'to_email', 'from_email', 'template', 'context', 'message')

    fieldsets = (
        (
            None, {
                'fields': (
                    'date',
                    'user',
                    'to_email',
                    'from_email',
                    'template',
                    'context',
                    'message'
                )
            }
        ),
    )


admin.site.register(MailModel, MailAdmin)
