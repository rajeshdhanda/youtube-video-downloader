import yt_dlp
import json
import os
import logging
import time
from pathlib import Path
import colorlog

# Important Parameters
JSON_FILE = "subjects.json"              # Name of the JSON file with subjects and URLs
LOG_FILE = "youtube_downloader.log"      # Name of the log file
BASE_DIR = os.getcwd()                   # Base directory (current working directory)
YDL_OPTS = {                             # yt-dlp configuration options
    'format': 'bestvideo+bestaudio/best',
    'merge_output_format': 'mp4',
    'quiet': False,
    'continuedl': True,
}

# Clear the log file before starting
if os.path.exists(LOG_FILE):
    open(LOG_FILE, 'w').close()  # Truncate the file to zero length

# Configure colorful logging
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    log_colors={
        'INFO': 'green',
        'ERROR': 'red',
        'WARNING': 'yellow',
    }
))

# File handler (no color in file, just plain text)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        file_handler,  # Plain text to file
        handler        # Colored output to console
    ]
)
logger = logging.getLogger(__name__)

def download_video(url: str, output_path: str) -> tuple[bool, float, int]:
    """
    Download a single video and return success status, duration, and file size.
    Handles errors internally and logs if file already exists.
    
    Args:
        url: YouTube video URL
        output_path: Directory to save the video
    
    Returns:
        tuple: (success_flag, download_duration_in_seconds, file_size_in_bytes)
    """
    ydl_opts = YDL_OPTS.copy()
    ydl_opts['outtmpl'] = f'{output_path}/%(title)s.%(ext)s'
    
    start_time = time.time()
    success = False
    file_size = 0
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'unknown_title')
            output_file = Path(output_path) / f"{video_title}.mp4"
            
            if output_file.exists():
                file_size = output_file.stat().st_size
                logger.info(f"Skipping download - video already exists: {output_file} "
                           f"(Size: {file_size / 1024 / 1024:.2f} MB)")
                return True, 0, file_size
            
            ydl.download([url])
            duration = time.time() - start_time
            file_size = output_file.stat().st_size if output_file.exists() else 0
            
            logger.info(f"Successfully downloaded: {url} to {output_file} "
                       f"(Size: {file_size / 1024 / 1024:.2f} MB, Time: {duration:.2f}s)")
            success = True
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Failed to download {url}: {str(e)}")
    
    return success, duration, file_size

def process_json_file(json_file_path: str, base_dir: str = BASE_DIR) -> dict:
    """
    Read JSON file, organize downloads by subject, and track metrics.
    Continues processing even if individual downloads fail.
    
    Args:
        json_file_path: Path to JSON file with subjects and URLs
        base_dir: Base directory for downloads (defaults to current directory)
    
    Returns:
        dict: Metrics including total files, successes, failures, total size, total time
    """
    metrics = {
        'total_videos': 0,
        'successful_downloads': 0,
        'failed_downloads': 0,
        'total_size_mb': 0,
        'total_time_s': 0
    }
    
    base_path = Path(base_dir)
    base_path.mkdir(exist_ok=True)
    logger.info(f"Using base directory: {base_path}")
    
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        
        for subject, urls in data.items():
            subject_path = base_path / subject
            subject_path.mkdir(exist_ok=True)
            logger.info(f"Processing subject: {subject} (Folder: {subject_path})")
            
            for url in urls:
                metrics['total_videos'] += 1
                logger.info(f"Starting download for {url} in {subject}")
                
                success, duration, file_size = download_video(url, str(subject_path))
                metrics['total_time_s'] += duration
                if success:
                    metrics['successful_downloads'] += 1
                    metrics['total_size_mb'] += file_size / 1024 / 1024
                else:
                    metrics['failed_downloads'] += 1
        
        logger.info(f"Download Summary: {metrics['successful_downloads']}/{metrics['total_videos']} "
                   f"successful, Total Size: {metrics['total_size_mb']:.2f} MB, "
                   f"Total Time: {metrics['total_time_s']:.2f}s")
        
    except FileNotFoundError:
        logger.error(f"JSON file '{json_file_path}' not found")
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in '{json_file_path}'")
    except Exception as e:
        logger.error(f"Error processing JSON: {str(e)}")
    
    return metrics


''' 
from pytube import Playlist

playlist = Playlist('https://www.youtube.com/playlist?list=PLG9zo4YEHArVQufUnDHr_gcFWcoNeJ-3i')
for url in playlist.video_urls:
    print(f'"{url}",')

'''

def main():
    """Main function to execute the downloader."""
    logger.info("Starting YouTube Downloader")
    metrics = process_json_file(JSON_FILE, BASE_DIR)
    logger.info("Download process completed")
    print(f"\nFinal Metrics: {metrics}")

if __name__ == "__main__":
    main()