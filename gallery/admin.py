from django.contrib import admin
from .models import Category, Photo


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'uploaded_at']
    list_filter = ['category', 'uploaded_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'uploaded_at'
