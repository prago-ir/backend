from django.contrib import admin, messages
from .models import Course, Episode, Chapter, Attribute, RoadMap
from adminsortable2.admin import SortableAdminMixin, SortableTabularInline
import uuid
from django.utils.text import slugify
from django.utils import timezone
from django.db import transaction


class AttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'value']
    search_fields = ['name', 'value']


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1
    fields = ['course', 'number', 'title', 'description']


class EpisodeInline(SortableTabularInline):
    model = Episode
    extra = 1
    fields = ['course', 'title', 'type',
              'content_url', 'order', 'file_size', 'status']


class ChapterAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ['number', 'title', 'course']
    list_filter = ['course']
    search_fields = ['title', 'description']
    ordering = ['number']

    inlines = [EpisodeInline]


def duplicate_selected_courses(modeladmin, request, queryset):
    duplicated_count = 0
    for original_course in queryset:
        try:
            with transaction.atomic():
                new_course = Course()

                # Fields to copy directly
                simple_fields_to_copy = [
                    'description', 'excerpt', 'intro_video_link',
                    'price', 'special_offer_price', 'special_offer_start_date', 'special_offer_end_date',
                    'cover_image'
                ]
                for field_name in simple_fields_to_copy:
                    setattr(new_course, field_name, getattr(
                        original_course, field_name))

                new_course.title = f"{original_course.title} (Copy)"
                new_course.latin_title = f"{original_course.latin_title}-copy" if original_course.latin_title else f"{slugify(original_course.title, allow_unicode=False)}-copy"
                if not new_course.latin_title:
                    new_course.latin_title = slugify(
                        new_course.title, allow_unicode=False) if new_course.title else f"course-{uuid.uuid4().hex[:6]}"

                base_slug_text = new_course.latin_title or new_course.title
                base_slug = slugify(base_slug_text, allow_unicode=False)
                if not base_slug:
                    base_slug = f"course-copy-{uuid.uuid4().hex[:4]}"

                temp_slug = base_slug
                counter = 1
                while Course.objects.filter(slug=temp_slug).exists():
                    temp_slug = f"{base_slug}-{counter}"
                    counter += 1
                new_course.slug = temp_slug

                # Default to draft, no published_at
                # Assuming 'draft' is a valid status
                course_status_draft = getattr(Course, 'DRAFT', 'draft')
                new_course.status = course_status_draft
                new_course.published_at = None

                new_course.save()  # Save to get an ID for relations

                # Copy ManyToMany relationships
                m2m_fields = ['organizers', 'teachers',
                              'attributes', 'tags', 'categories']
                for field_name in m2m_fields:
                    if hasattr(original_course, field_name) and hasattr(new_course, field_name):
                        original_m2m_manager = getattr(
                            original_course, field_name)
                        new_m2m_manager = getattr(new_course, field_name)
                        new_m2m_manager.set(original_m2m_manager.all())

                # Duplicate Chapters
                original_chapters = original_course.chapters.all().order_by('number')
                for original_chapter in original_chapters:
                    new_chapter = Chapter()
                    new_chapter.course = new_course
                    new_chapter.number = original_chapter.number
                    # No (Copy) for chapters/episodes by default
                    new_chapter.title = f"{original_chapter.title}"
                    new_chapter.description = original_chapter.description
                    new_chapter.save()

                    # Duplicate Episodes for each chapter
                    original_episodes = original_chapter.episodes.all().order_by('order')
                    # Assuming 'draft' is a valid status
                    episode_status_draft = getattr(Episode, 'DRAFT', 'draft')
                    for original_episode in original_episodes:
                        new_episode = Episode()
                        new_episode.chapter = new_chapter
                        new_episode.course = new_course

                        episode_fields_to_copy = [
                            'title', 'type', 'content_url', 'description',
                            'thumbnail', 'file_size', 'word_count', 'order'
                        ]
                        for field_name in episode_fields_to_copy:
                            setattr(new_episode, field_name, getattr(
                                original_episode, field_name))

                        new_episode.status = episode_status_draft
                        new_episode.published_at = None
                        new_episode.save()

                new_course.save()  # Save again to update calculated fields like total_hours
                duplicated_count += 1
        except Exception as e:
            modeladmin.message_user(
                request, f"Error duplicating course '{original_course.title}': {e}", messages.ERROR)

    if duplicated_count > 0:
        modeladmin.message_user(
            request, f"Successfully duplicated {duplicated_count} course(s). New courses are set to 'draft'.", messages.SUCCESS)
    else:
        modeladmin.message_user(
            request, "No courses were duplicated. Check for errors.", messages.WARNING)


duplicate_selected_courses.short_description = "Duplicate selected courses"


def publish_selected_courses(modeladmin, request, queryset):
    published_count = 0
    # To count courses that were already published but perhaps had episodes updated
    updated_count = 0

    course_status_published = getattr(Course, 'PUBLISHED', 'published')
    episode_status_published = getattr(Episode, 'PUBLISHED', 'published')

    for course in queryset:
        try:
            with transaction.atomic():
                course_was_already_published = (
                    course.status == course_status_published and course.published_at is not None)

                if course.status != course_status_published:
                    course.status = course_status_published
                    if course.published_at is None:  # Only set published_at if it's not already set
                        course.published_at = timezone.now()
                    course.save()
                    published_count += 1
                elif not course_was_already_published and course.published_at is None:  # Was marked published but no date
                    course.published_at = timezone.now()
                    course.save()
                    updated_count += 1  # Count as updated rather than newly published
                else:
                    # Course was already published and had a date, count for episode updates
                    updated_count += 1

                # Publish all episodes within the course
                # Or filter by status if needed, e.g., .filter(status='draft')
                episodes_to_publish = course.episodes.all()
                for episode in episodes_to_publish:
                    if episode.status != episode_status_published:
                        episode.status = episode_status_published
                        if episode.published_at is None:
                            episode.published_at = timezone.now()
                        episode.save()
                    elif episode.published_at is None:  # Was marked published but no date
                        episode.published_at = timezone.now()
                        episode.save()

                # If the course was already published, we don't increment published_count
                # but it will fall into updated_count if episodes were changed.
                # If it was newly published, it's already in published_count.

        except Exception as e:
            modeladmin.message_user(
                request, f"Error publishing course '{course.title}': {e}", messages.ERROR)

    if published_count > 0:
        modeladmin.message_user(
            request, f"Successfully published {published_count} course(s) and their episodes.", messages.SUCCESS)
    if updated_count > 0 and published_count == 0:  # Only show if no new ones were published
        modeladmin.message_user(
            request, f"{updated_count} course(s) were already published (episodes status checked/updated).", messages.INFO)
    elif updated_count > 0 and published_count > 0:  # If some were new, and some were updates
        modeladmin.message_user(
            request, f"Additionally, {updated_count} course(s) were already published (episodes status checked/updated).", messages.INFO)


publish_selected_courses.short_description = "Publish selected courses (and their episodes)"


class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'latin_title', 'status',
                    'published_at', 'total_hours', 'created_at']
    list_filter = ['status', 'categories', 'tags', 'teachers', 'organizers']
    search_fields = ['title', 'latin_title', 'description']
    prepopulated_fields = {'slug': ('latin_title',)}
    filter_horizontal = ['organizers', 'teachers',
                         'attributes', 'tags', 'categories']
    fieldsets = [
        ('Course Information', {'fields': [
         'cover_image', 'title', 'latin_title', 'slug', 'description', 'excerpt', 'intro_video_link', 'total_hours']}),
        ('Publication', {'fields': ['status', 'published_at']}),
        ('Pricing', {'fields': ['price', 'special_offer_price',
         'special_offer_start_date', 'special_offer_end_date']}),
        ('Relationships', {'fields': [
         'organizers', 'teachers', 'attributes', 'tags', 'categories']}),
    ]
    inlines = [ChapterInline]
    readonly_fields = ['published_at', 'total_hours']
    actions = [duplicate_selected_courses,
               publish_selected_courses]  # Add the new action


class EpisodeAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ['order', 'title', 'chapter', 'type',
                    'status', 'published_at', 'duration', 'file_size']
    list_filter = ['status', 'course', 'chapter', 'type']
    search_fields = ['title', 'description']
    autocomplete_fields = ['course', 'chapter']
    fieldsets = [
        ('Basic Information', {'fields': [
         'title', 'course', 'chapter', 'type', 'order']}),
        ('Publication', {'fields': ['status', 'published_at']}),
        ('Content', {'fields': ['thumbnail', 'content_url', 'description']}),
        # Added duration
        ('Media Details', {'fields': ['file_size', 'word_count', 'duration']}),
    ]
    readonly_fields = ['published_at', 'duration']  # Added duration


class RoadmapAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at', 'status']
    search_fields = ['name', 'description']
    filter_horizontal = ['courses']
    ordering = ['created_at']
    readonly_fields = ['created_at']


# Register models
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(Chapter, ChapterAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Episode, EpisodeAdmin)
admin.site.register(RoadMap, RoadmapAdmin)
