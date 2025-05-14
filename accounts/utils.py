def save_profile_picture(profile, picture_url, sub):
    """
    Download and save the profile picture locally

    Args:
        profile: User profile model instance
        picture_url: URL of the image to download
        sub: Subject identifier (unique user ID)

    Returns:
        bool: True if successful, False otherwise
    """
    import requests
    from django.core.files.base import ContentFile
    import os
    from io import BytesIO
    from django.core.files.images import ImageFile

    try:
        # Download the image
        response = requests.get(picture_url, stream=True)
        response.raise_for_status()  # Raise exception if request failed

        # Get file extension from content type
        content_type = response.headers.get('Content-Type', '')
        extension = get_extension_from_content_type(content_type)

        # Create a unique filename
        filename = f"google_profile_{sub}_{os.urandom(4).hex()}{extension}"

        # Save the file to the profile model
        file_content = ContentFile(response.content)
        profile.avatar.save(filename, file_content, save=True)

        # Log success
        print(
            f"Successfully saved profile picture for user {profile.user.email}")
        return True

    except Exception as e:
        # Log the error but don't fail the registration process
        print(f"Failed to save profile picture: {str(e)}")
        return False


def get_extension_from_content_type(content_type):
    """
    Map content type to appropriate file extension

    Args:
        content_type: HTTP Content-Type header value

    Returns:
        str: File extension including the dot (e.g., '.jpg')
    """
    content_type_map = {
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
    }
    # Default to jpg if unknown
    return content_type_map.get(content_type, '.jpg')
