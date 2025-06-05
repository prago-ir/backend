from django.contrib import admin
from .models import Post  # Import the Post model


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'get_author_name',
                    'get_status_display', 'published_at', 'created_at', 'updated_at')
    list_filter = ('status', 'author', 'categories', 'tags', 'published_at')
    search_fields = ('title', 'content', 'excerpt', 'slug',
                     'author__username')  # Assuming author has a username
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-published_at',)
    filter_horizontal = ('categories', 'tags',)

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'status', 'published_at')
        }),
        ('Content', {
            'fields': ('content', 'excerpt', 'featured_image')
        }),
        ('Taxonomy', {
            'fields': ('categories', 'tags')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  # Make this section collapsible
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def get_author_name(self, obj):
        if obj.author:
            # Assuming your Author model or User model has a 'get_full_name' method or a 'username' field
            if hasattr(obj.author, 'get_full_name') and callable(obj.author.get_full_name):
                return obj.author.get_full_name()
            return obj.author.username  # Fallback to username
        return None
    get_author_name.short_description = 'Author'  # Column header in admin

    # If you have a 'status' field with choices, get_status_display is automatically available.
    # If not, and 'status' is just a CharField, you can remove 'get_status_display'
    # from list_display and just use 'status'.

# If you prefer a simpler registration without customizations, you can just do:
# admin.site.register(Post)
