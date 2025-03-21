from django.contrib import admin
from .models import Course, Episode, Chapter, Attribute


class AttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'value']
    search_fields = ['name', 'value']


class ChapterAdmin(admin.ModelAdmin):
    list_display = ['number', 'title']
    list_filter = ['number']
    search_fields = ['title', 'description']


class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 1
    fields = ['title', 'type', 'order', 'duration', 'file_size']


class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'price', 'special_offer_price', 'has_active_special_offer', 'total_hours', 'created_at']
    list_filter = ['categories', 'tags', 'teachers', 'organizers']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['organizers', 'teachers', 'attributes', 'tags', 'categories']
    fieldsets = [
        ('Course Information', {'fields': ['cover_image', 'title', 'slug', 'description', 'intro_video_link', 'total_hours']}),
        ('Pricing', {'fields': ['price', 'special_offer_price', 'special_offer_start_date', 'special_offer_end_date']}),
        ('Relationships', {'fields': ['organizers', 'teachers', 'attributes', 'tags', 'categories']}),
    ]
    inlines = [EpisodeInline]
    
    def has_active_special_offer(self, obj):
        return obj.has_active_special_offer()
    has_active_special_offer.boolean = True
    has_active_special_offer.short_description = "Active Special Offer"


class EpisodeAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'chapter', 'type', 'order', 'duration', 'file_size']
    list_filter = ['course', 'chapter', 'type']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['course', 'chapter']
    fieldsets = [
        ('Basic Information', {'fields': ['title', 'slug', 'course', 'chapter', 'type', 'order']}),
        ('Content', {'fields': ['thumbnail', 'content_url', 'description']}),
        ('Media Details', {'fields': ['duration', 'file_size', 'word_count']}),
    ]


# Register models
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(Chapter, ChapterAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Episode, EpisodeAdmin)
