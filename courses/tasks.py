import logging
from celery import shared_task
from django.db.models import Sum
from .models import Episode, Course
from .utils import get_hls_duration

logger = logging.getLogger(__name__)

@shared_task
def process_video_metadata(episode_id):
    """
    Task to process video metadata including duration for an episode
    
    Args:
        episode_id (int): The ID of the Episode model instance
    """
    try:
        episode = Episode.objects.get(id=episode_id)
        
        # Only process video type episodes with a content URL and no duration set
        if episode.type == 'video' and episode.content_url and not episode.duration:
            logger.info(f"Processing video metadata for episode {episode_id}")
            
            duration = get_hls_duration(episode.content_url)
            
            if duration:
                episode.duration = duration
                episode.save(update_fields=['duration'])
                logger.info(f"Updated duration for episode {episode_id}: {duration}")
            else:
                logger.warning(f"Could not determine duration for episode {episode_id}")
        
        return True
    except Episode.DoesNotExist:
        logger.error(f"Episode with ID {episode_id} does not exist")
    except Exception as e:
        logger.error(f"Error processing video metadata for episode {episode_id}: {e}")
        raise

@shared_task
def update_course_total_hours(course_id):
    """
    Calculate the total duration of all published video episodes in a course
    and update the course's total_hours field.
    """
    try:
        course = Course.objects.get(id=course_id)
        
        # Get all published video episodes with duration
        total_seconds = Episode.objects.filter(
            course=course,
            type='video',
            status='published',
            duration__isnull=False
        ).aggregate(
            total_duration=Sum('duration')
        )['total_duration']
        
        # Convert to hours with one decimal place
        if total_seconds is not None:
            total_hours = round(total_seconds.total_seconds() / 3600, 1)
            course.total_hours = total_hours
            course.save(update_fields=['total_hours'])
            
            # Format the duration nicely for logs
            hours = int(total_seconds.total_seconds() // 3600)
            minutes = int((total_seconds.total_seconds() % 3600) // 60)
            seconds = int(total_seconds.total_seconds() % 60)
            formatted_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            logger.info(f"Updated total hours for course {course.id}: {total_hours} hours (total duration: {formatted_duration})")
        else:
            course.total_hours = 0
            course.save(update_fields=['total_hours'])
            logger.info(f"No video episodes with duration for course {course.id}")
            
        return f"Course {course.id} total hours updated to {course.total_hours}"
    except Course.DoesNotExist:
        logger.error(f"Course with ID {course_id} not found")
        return f"Error: Course with ID {course_id} not found"
    except Exception as e:
        logger.error(f"Error updating total hours for course {course_id}: {str(e)}")
        return f"Error: {str(e)}"