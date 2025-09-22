from django.contrib import admin
from .models import News


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['subject', 'posted_on', 'display_on_home']
    list_filter = ['posted_on', 'display_on_home']
    search_fields = ['subject', 'body']
    date_hierarchy = 'posted_on'
    list_editable = ['display_on_home']
