from django.contrib import admin, messages
from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'get_author_name', 'get_status_display',
                    'is_pinned', 'published_at', 'created_at', 'updated_at')
    list_filter = ('status', 'is_pinned', 'author', 'categories',
                   'tags', 'published_at')
    search_fields = ('title', 'content', 'excerpt', 'slug',
                     # Updated search fields
                     'author__user__username', 'author__user__first_name', 'author__user__last_name')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-is_pinned', '-published_at',)
    filter_horizontal = ('categories', 'tags',)

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'status', 'is_pinned', 'published_at')
        }),
        ('Content', {
            'fields': ('content', 'excerpt', 'featured_image')
        }),
        ('Taxonomy', {
            'fields': ('categories', 'tags')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def get_author_name(self, obj):
        if obj.author and obj.author.user:  # Check if author and user exist
            if obj.author.user.get_full_name():
                return obj.author.user.get_full_name()
            return obj.author.user.username  # Fallback to username
        return "N/A"  # Or some other placeholder
    get_author_name.short_description = 'Author'

    # --- Admin Actions ---
    def pin_selected_posts(self, request, queryset):
        updated_count = queryset.update(is_pinned=True)
        self.message_user(
            request, f"{updated_count} post(s) successfully pinned.", messages.SUCCESS)
    pin_selected_posts.short_description = "Pin selected posts"

    def unpin_selected_posts(self, request, queryset):
        updated_count = queryset.update(is_pinned=False)
        self.message_user(
            request, f"{updated_count} post(s) successfully unpinned.", messages.SUCCESS)
    unpin_selected_posts.short_description = "Unpin selected posts"

    actions = ['pin_selected_posts',
               'unpin_selected_posts']  # Add actions here

# If you prefer a simpler registration without customizations, you can just do:
# admin.site.register(Post)
