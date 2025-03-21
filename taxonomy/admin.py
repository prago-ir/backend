from django.contrib import admin
from .models import Category, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'latin_name', 'slug', 'parent', 'content_type')
    list_filter = ('content_type', 'parent')
    search_fields = ('name', 'latin_name', 'slug')
    prepopulated_fields = {'slug': ('latin_name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'latin_name', 'slug', 'content_type')
    list_filter = ('content_type',)
    search_fields = ('name', 'latin_name', 'slug')
    prepopulated_fields = {'slug': ('latin_name',)}
