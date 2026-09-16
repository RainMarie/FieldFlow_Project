import os
import logging
import threading
from PIL import Image, ImageEnhance

# 1. Set up standard system logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 2. Dynamic Path Resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # Points to src/backend/
SRC_DIR = os.path.dirname(CURRENT_DIR)                    # Points to src/
ROOT_DIR = os.path.dirname(SRC_DIR)                       # Points to FieldFlow_Project/

# 3. Define the exact path to our temporary media holding drawer
STAGING_DIR = os.path.join(ROOT_DIR, "assets", "temp_media")


def ensure_staging_perimeter():
    """
    ELI5: Checks if our temporary image folder exists. 
    If it's missing, it builds it automatically so the app doesn't crash.
    """
    if not os.path.exists(STAGING_DIR):
        logging.info(f"Staging directory missing. Creating perimeter at: {STAGING_DIR}")
        os.makedirs(STAGING_DIR, exist_ok=True)
    else:
        logging.info(f"Staging directory verified active at: {STAGING_DIR}")


def compress_profile_a(input_image_path, filename):
    """
    ELI5: Takes a high-res technician photo of a data plate, forces it into a max 1080p box, 
    and compresses it beautifully so text is 100% readable but the file size stays light.
    """
    try:
        # Open the raw image file using Pillow
        with Image.open(input_image_path) as img:
            
            # Enforce the 1920x1080 resolution boundary proportionally
            max_width, max_height = 1920, 1080
            width, height = img.size
            
            # Only downscale if the image is physically larger than our boundary
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_size = (int(width * ratio), int(height * ratio))
                logging.info(f"Downscaling Profile A image from {img.size} to {new_size}")
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert image mode to RGB if it happens to be in a different format
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            # Dynamic Compression Loop: Target 150KB - 300KB footprint
            output_path = os.path.join(STAGING_DIR, filename)
            target_quality = 75  # Start at high-end quality threshold
            
            img.save(output_path, "JPEG", quality=target_quality, optimize=True)
            file_size_kb = os.path.getsize(output_path) / 1024
            
            # Security Valve: If file size is still too heavy, step quality down safely to 65%
            if file_size_kb > 300.0 and target_quality > 65:
                target_quality = 65
                logging.info(f"Image footprint ({file_size_kb:.1f}KB) exceeds 300KB limit. Compressing to quality {target_quality}...")
                img.save(output_path, "JPEG", quality=target_quality, optimize=True)
                file_size_kb = os.path.getsize(output_path) / 1024
                
            logging.info(f"Profile A optimization complete: Saved {filename} ({file_size_kb:.1f} KB) at quality {target_quality}%")
            return output_path

    except Exception as e:
        logging.error(f"Critical error executing Profile A processing layer: {str(e)}")
        return None


def compress_profile_b(input_image_path, filename):
    """
    ELI5: Takes a technician's photo of a paper receipt, strips out all color, 
    cranks up the contrast so faint ink becomes readable, and shrinks it to under 100KB.
    """
    try:
        # Open the raw receipt image using Pillow
        with Image.open(input_image_path) as img:
            
            # Mandatory Grayscale Conversion (L Mode = Luminance/B&W)
            logging.info(f"Converting Profile B image {filename} to grayscale...")
            img = img.convert("L")
            
            # Prevent Contrast Loss: Artificially boost edge contrast by 50%
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)  # 1.5 multiplier = 50% contrast boost
            
            # Enforce the 1280x720 resolution boundary proportionally
            max_width, max_height = 1280, 720
            width, height = img.size
            
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_size = (int(width * ratio), int(height * ratio))
                logging.info(f"Downscaling Profile B receipt from {img.size} to {new_size}")
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
            # Dynamic Compression Loop: Target 50KB - 100KB footprint
            output_path = os.path.join(STAGING_DIR, filename)
            target_quality = 60  # Start at the top of our Profile B quality bracket
            
            img.save(output_path, "JPEG", quality=target_quality, optimize=True)
            file_size_kb = os.path.getsize(output_path) / 1024
            
            # Security Valve: If file size is still over 100KB, drop quality to 50%
            if file_size_kb > 100.0 and target_quality > 50:
                target_quality = 50
                logging.info(f"Receipt footprint ({file_size_kb:.1f}KB) exceeds 100KB. Scaling down quality to {target_quality}...")
                img.save(output_path, "JPEG", quality=target_quality, optimize=True)
                file_size_kb = os.path.getsize(output_path) / 1024
                
            logging.info(f"Profile B optimization complete: Saved {filename} ({file_size_kb:.1f} KB) at quality {target_quality}%")
            return output_path

    except Exception as e:
        logging.error(f"Critical error executing Profile B receipt processing layer: {str(e)}")
        return None


def process_media_in_background(profile_type, input_image_path, filename, on_success_callback=None):
    """
    ELI5: Spins up a secret background helper thread to compress the photo.
    This guarantees the app interface never freezes or stutters for the technician.
    """
    def worker():
        logging.info(f"Background worker thread started for media optimization: {filename}")
        if profile_type.upper() == "A":
            optimized_path = compress_profile_a(input_image_path, filename)
        elif profile_type.upper() == "B":
            optimized_path = compress_profile_b(input_image_path, filename)
        else:
            logging.error(f"Invalid compression profile profile_type requested: {profile_type}")
            optimized_path = None
            
        # If a callback function was provided, notify the UI engine that the file is ready
        if on_success_callback and optimized_path:
            on_success_callback(optimized_path)

    # Instantiate and launch the thread safely as a background daemon
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    logging.info(f"Media processing thread successfully detached for execution: {filename}")


def purge_cached_media_file(filename):
    """
    ELI5: Wipes out a local image file from the device storage.
    This is triggered by the 7-day cache sweep script to prevent storage bloat.
    """
    try:
        target_file = os.path.join(STAGING_DIR, filename)
        if os.path.exists(target_file):
            os.remove(target_file)
            logging.info(f"7-Day Cache Sweep: Successfully deleted expired binary file: {filename}")
            return True
        else:
            logging.warning(f"7-Day Cache Sweep Warning: Targeted file not found on disk: {filename}")
            return False
    except Exception as e:
        logging.error(f"Critical error executing cache media file purge: {str(e)}")
        return False


# 4. Trigger the safety check immediately when this module is initialized
ensure_staging_perimeter()

