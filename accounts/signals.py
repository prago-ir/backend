from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import MyUser, Profile, Teacher, Organizer, Author

@receiver(post_save, sender=MyUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a profile for every new user"""
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=Teacher)
def add_to_teacher_group(sender, instance, created, **kwargs):
    """Add user to the Teacher group when a Teacher is created"""
    if created and instance.user:
        teacher_group, _ = Group.objects.get_or_create(name='Teachers')
        instance.user.groups.add(teacher_group)

@receiver(post_delete, sender=Teacher)
def remove_from_teacher_group(sender, instance, **kwargs):
    """Remove user from the Teacher group when a Teacher is deleted"""
    teacher_group = Group.objects.filter(name='Teachers').first()
    if teacher_group:
        instance.user.groups.remove(teacher_group)

@receiver(post_save, sender=Organizer)
def add_to_organizer_group(sender, instance, created, **kwargs):
    """Add user to the Organizer group when an Organizer is created"""
    if created and instance.user:
        organizer_group, _ = Group.objects.get_or_create(name='Organizers')
        instance.user.groups.add(organizer_group)

@receiver(post_delete, sender=Organizer)
def remove_from_organizer_group(sender, instance, **kwargs):
    """Remove user from the Organizer group when an Organizer is deleted"""
    organizer_group = Group.objects.filter(name='Organizers').first()
    if organizer_group:
        instance.user.groups.remove(organizer_group)

@receiver(post_save, sender=Author)
def add_to_author_group(sender, instance, created, **kwargs):
    """Add user to the Author group when an Author is created"""
    if created and instance.user:
        author_group, _ = Group.objects.get_or_create(name='Authors')
        instance.user.groups.add(author_group)

@receiver(post_delete, sender=Author)
def remove_from_author_group(sender, instance, **kwargs):
    """Remove user from the Author group when an Author is deleted"""
    author_group = Group.objects.filter(name='Authors').first()
    if author_group:
        instance.user.groups.remove(author_group)