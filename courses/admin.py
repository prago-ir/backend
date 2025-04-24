from django.contrib import admin
from .models import Course, Episode, Chapter, Attribute


class AttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'value']
    search_fields = ['name', 'value']



class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1
    fields = ['course','number', 'title', 'description']


class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 1
    fields = ['course', 'title', 'type', 'content_url','order', 'duration', 'file_size', 'status']


class ChapterAdmin(admin.ModelAdmin):
    list_display = [ 'title', 'number', 'course']
    list_filter = ['course']
    search_fields = ['title', 'description']
    
    inlines = [EpisodeInline]


class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'latin_title', 'status', 'published_at', 'price', 'special_offer_price', 'has_active_special_offer', 'total_hours', 'created_at']
    list_filter = ['status', 'categories', 'tags', 'teachers', 'organizers']
    search_fields = ['title', 'latin_title', 'description']
    prepopulated_fields = {'slug': ('latin_title',)}
    filter_horizontal = ['organizers', 'teachers', 'attributes', 'tags', 'categories']
    fieldsets = [
        ('Course Information', {'fields': ['cover_image', 'title', 'latin_title', 'slug', 'description', 'intro_video_link', 'total_hours']}),
        ('Publication', {'fields': ['status', 'published_at']}),
        ('Pricing', {'fields': ['price', 'special_offer_price', 'special_offer_start_date', 'special_offer_end_date']}),
        ('Relationships', {'fields': ['organizers', 'teachers', 'attributes', 'tags', 'categories']}),
    ]
    inlines = [ChapterInline]
    readonly_fields = ['published_at']
    
    def has_active_special_offer(self, obj):
        return obj.has_active_special_offer()
    has_active_special_offer.boolean = True
    has_active_special_offer.short_description = "Active Special Offer"


class EpisodeAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'chapter', 'type', 'status', 'published_at', 'order', 'duration', 'file_size']
    list_filter = ['status', 'course', 'chapter', 'type']
    search_fields = ['title', 'description']
    autocomplete_fields = ['course', 'chapter']
    fieldsets = [
        ('Basic Information', {'fields': ['title', 'course', 'chapter', 'type', 'order']}),
        ('Publication', {'fields': ['status', 'published_at']}),
        ('Content', {'fields': ['thumbnail', 'content_url', 'description']}),
        ('Media Details', {'fields': ['duration', 'file_size', 'word_count']}),
    ]
    readonly_fields = ['published_at']


# Register models
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(Chapter, ChapterAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Episode, EpisodeAdmin)
