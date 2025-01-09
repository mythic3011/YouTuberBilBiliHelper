from flask import Flask, request, jsonify, Response
import redis
import logging
import os
import yt_dlp
import time
from urllib.parse import urlparse
import requests
import shutil

app = Flask(__name__)

# Configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", 60))  # seconds
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", 10))
DOWNLOAD_DIRECTORY = os.environ.get("DOWNLOAD_DIRECTORY", "downloads")
MAX_STORAGE_GB = int(os.environ.get("MAX_STORAGE_GB", 10))
MAX_STORAGE_BYTES = MAX_STORAGE_GB * 1024 * 1024 * 1024

# Logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Redis client
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)

def is_youtube_url(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc in ["www.youtube.com", "youtube.com", "m.youtube.com"]

def is_bilibili_url(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc in ["www.bilibili.com", "bilibili.com", "m.bilibili.com"]

def get_domain_from_url(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

def apply_rate_limit(identifier):
    key = f"rate_limit:{identifier}"
    now = int(time.time())
    with redis_client.pipeline() as pipe:
        pipe.zadd(key, {now: now})
        pipe.zremrangebyscore(key, 0, now - RATE_LIMIT_WINDOW)
        pipe.zcard(key)
        pipe.expire(key, RATE_LIMIT_WINDOW)
        _, _, request_count = pipe.execute()
    if request_count > RATE_LIMIT_MAX_REQUESTS:
        return False
    return True

def get_downloaded_files_size():
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(DOWNLOAD_DIRECTORY):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def enforce_storage_limit():
    current_size = get_downloaded_files_size()
    if current_size > MAX_STORAGE_BYTES:
        logging.warning(
            f"Storage limit exceeded. Current size: {current_size / (1024**3):.2f} GB, Limit: {MAX_STORAGE_GB} GB"
        )
        # Implement logic to delete older files. A simple approach is to delete by modification time.
        files = []
        for dirpath, dirnames, filenames in os.walk(DOWNLOAD_DIRECTORY):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                files.append((filepath, os.path.getmtime(filepath)))

        files.sort(key=lambda item: item[1])  # Sort by modification time (oldest first)

        bytes_to_free = current_size - MAX_STORAGE_BYTES
        freed_bytes = 0
        for filepath, _ in files:
            try:
                deleted_size = os.path.getsize(filepath)
                os.remove(filepath)
                freed_bytes += deleted_size
                logging.info(f"Deleted file to free up space: {filepath}")
                if freed_bytes >= bytes_to_free:
                    logging.info(f"Freed up enough space: {freed_bytes / (1024**2):.2f} MB")
                    break
            except Exception as e:
                logging.error(f"Error deleting file {filepath}: {e}")

@app.before_request
def rate_limiting():
    client_ip = request.remote_addr
    if not apply_rate_limit(client_ip):
        logging.warning(f"Rate limit exceeded for IP: {client_ip}")
        return jsonify({"error": "Too many requests"}, 429)

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    logging.error(f"Unexpected error: {error}")
    return jsonify({"error": "An unexpected error occurred."}, 500)

@app.route("/youtube/download/video", methods=["POST"])
def download_youtube_video():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing video URL"}, 400)
    video_url = data["url"]

    if not is_youtube_url(video_url):
        return jsonify({"error": "Invalid YouTube URL"}, 400)

    try:
        ydl_opts = {
            "outtmpl": os.path.join(DOWNLOAD_DIRECTORY, "youtube/%(title)s.%(ext)s"),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            video_filename = ydl.prepare_filename(info_dict)
            enforce_storage_limit()
            return jsonify({"message": "YouTube video download started", "filename": video_filename}), 200
    except Exception as e:
        logging.error(f"Error downloading YouTube video: {e}")
        return jsonify({"error": f"Failed to download YouTube video: {str(e)}"}, 500)

@app.route("/youtube/download/playlist", methods=["POST"])
def download_youtube_playlist():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing playlist URL"}, 400)
    playlist_url = data["url"]

    if not is_youtube_url(playlist_url):
        return jsonify({"error": "Invalid YouTube playlist URL"}, 400)

    try:
        ydl_opts = {
            "outtmpl": os.path.join(DOWNLOAD_DIRECTORY, "youtube/%(playlist)s/%(title)s.%(ext)s"),
            "extract_flat": True,  # Only get video information, not download yet
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            if playlist_info and "entries" in playlist_info:
                for entry in playlist_info["entries"]:
                    if entry and "url" in entry:
                        video_url = entry["url"]
                        try:
                            ydl_opts_single = {
                                "outtmpl": os.path.join(DOWNLOAD_DIRECTORY, "youtube/%(playlist)s/%(title)s.%(ext)s"),
                            }
                            with yt_dlp.YoutubeDL(ydl_opts_single) as ydl_single:
                                ydl_single.download([video_url])
                                enforce_storage_limit()
                        except Exception as e:
                            logging.error(f"Error downloading video from playlist {playlist_url}: {e}")
                return jsonify({"message": "YouTube playlist download started"}), 200
            else:
                return jsonify({"error": "Could not retrieve playlist information"}, 500)
    except Exception as e:
        logging.error(f"Error processing YouTube playlist: {e}")
        return jsonify({"error": f"Failed to process YouTube playlist: {str(e)}"}, 500)

@app.route("/youtube/stream/video", methods=["POST"])
def stream_youtube_video():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing video URL"}, 400)
    video_url = data["url"]

    if not is_youtube_url(video_url):
        return jsonify({"error": "Invalid YouTube URL"}, 400)

    try:
        ydl_opts = {
            "format": "best[protocol!=http_dash_segments]",  # Get the best non-DASH format
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            if 'url' in info_dict:
                video_url_stream = info_dict['url']
                response = requests.get(video_url_stream, stream=True)
                return Response(response.iter_content(chunk_size=1024),
                                content_type=response.headers['Content-Type'])
            else:
                return jsonify({"error": "Could not retrieve direct video URL"}, 500)
    except Exception as e:
        logging.error(f"Error streaming YouTube video: {e}")
        return jsonify({"error": f"Failed to stream YouTube video: {str(e)}"}, 500)

@app.route("/bilibili/download/video", methods=["POST"])
def download_bilibili_video():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing video URL"}, 400)
    video_url = data["url"]

    if not is_bilibili_url(video_url):
        return jsonify({"error": "Invalid Bilibili URL"}, 400)

    try:
        ydl_opts = {
            "outtmpl": os.path.join(DOWNLOAD_DIRECTORY, "bilibili/%(title)s.%(ext)s"),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            video_filename = ydl.prepare_filename(info_dict)
            enforce_storage_limit()
            return jsonify({"message": "Bilibili video download started", "filename": video_filename}), 200
    except Exception as e:
        logging.error(f"Error downloading Bilibili video: {e}")
        return jsonify({"error": f"Failed to download Bilibili video: {str(e)}"}, 500)

@app.route("/bilibili/download/playlist", methods=["POST"])
def download_bilibili_playlist():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing playlist URL"}, 400)
    playlist_url = data["url"]

    if not is_bilibili_url(playlist_url):
        return jsonify({"error": "Invalid Bilibili playlist URL"}, 400)

    try:
        ydl_opts = {
            "outtmpl": os.path.join(DOWNLOAD_DIRECTORY, "bilibili/%(playlist)s/%(title)s.%(ext)s"),
            "extract_flat": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            if playlist_info and "entries" in playlist_info:
                for entry in playlist_info["entries"]:
                    if entry and "url" in entry:
                        video_url = entry["url"]
                        try:
                            ydl_opts_single = {
                                "outtmpl": os.path.join(DOWNLOAD_DIRECTORY, "bilibili/%(playlist)s/%(title)s.%(ext)s"),
                            }
                            with yt_dlp.YoutubeDL(ydl_opts_single) as ydl_single:
                                ydl_single.download([video_url])
                                enforce_storage_limit()
                        except Exception as e:
                            logging.error(f"Error downloading video from Bilibili playlist {playlist_url}: {e}")
                return jsonify({"message": "Bilibili playlist download started"}), 200
            else:
                return jsonify({"error": "Could not retrieve Bilibili playlist information"}, 500)
    except Exception as e:
        logging.error(f"Error processing Bilibili playlist: {e}")
        return jsonify({"error": f"Failed to process Bilibili playlist: {str(e)}"}, 500)

@app.route("/bilibili/stream/video", methods=["POST"])
def stream_bilibili_video():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing video URL"}, 400)
    video_url = data["url"]

    if not is_bilibili_url(video_url):
        return jsonify({"error": "Invalid Bilibili URL"}, 400)

    try:
        ydl_opts = {
            "format": "best[protocol!=http_dash_segments]",  # Get the best non-DASH format
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            if 'url' in info_dict:
                video_url_stream = info_dict['url']
                response = requests.get(video_url_stream, stream=True)
                return Response(response.iter_content(chunk_size=1024),
                                content_type=response.headers['Content-Type'])
            else:
                return jsonify({"error": "Could not retrieve direct video URL"}, 500)
    except Exception as e:
        logging.error(f"Error streaming Bilibili video: {e}")
        return jsonify({"error": f"Failed to stream Bilibili video: {str(e)}"}, 500)

if __name__ == "__main__":
    app.run(debug=True)