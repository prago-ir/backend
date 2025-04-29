import subprocess
import json
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

def get_hls_duration(hls_url):
    """
    Extract duration from an HLS stream using ffprobe
    
    Args:
        hls_url (str): The URL to the HLS stream
        
    Returns:
        timedelta: The duration of the video as a Python timedelta object
        None: If there was an error extracting the duration
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            hls_url
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        
        if result.returncode != 0:
            logger.error(f"ffprobe command failed: {result.stderr}")
            return None
            
        data = json.loads(result.stdout)
        
        if 'format' not in data or 'duration' not in data['format']:
            logger.error(f"Duration not found in ffprobe output")
            return None
            
        duration_seconds = int(data['format']['duration'])
        duration = timedelta(seconds=duration_seconds)
        
        logger.info(f"Successfully extracted duration: {duration} from {hls_url}")
        return duration
    except Exception as e:
        logger.error(f"Error getting HLS duration: {e}")
        return None