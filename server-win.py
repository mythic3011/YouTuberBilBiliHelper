import datetime
import asyncpg
from flask import Flask, jsonify, request, send_file, redirect
import pytube
import os
import uuid
import glob
from waitress import serve
import logging
from logging.handlers import RotatingFileHandler
from flask_limiter import Limiter
import asyncio
import aioredis

app = Flask(__name__)
limiter = Limiter(app, key_prefix='rate-limit')

async def create_redis_pool():
    redis_url = os.getenv('REDIS_URL', 'redis://127.0.0.1:16379')
    return await aioredis.create_redis_pool(redis_url)

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

redis_pool = asyncio.run(create_redis_pool())

downloaded_videos:dict = {}
download_dir = 'downloads'

date = datetime.datetime.now().strftime("%Y-%m-%d")
log_file = f'app-{date}.log'
log_path = f'logs/{date}'
log_handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=5)
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_handler.setFormatter(log_formatter)
app.logger.addHandler(log_handler)
app.logger.setLevel(logging.INFO)

@app.route('/api/v1/', methods=['GET'])
@limiter.limit('10/minute', key_func=lambda: request.remote_addr)
async def api_raw_link():
    video_url = request.args.get('yt', default=None, type=str)
    if (video_url and "youtube.com/watch?v=" in video_url
            or "youtu.be/" in video_url
            or "bilibili.com/video/" in video_url):
        try:
            key = f"{request.remote_addr}:{request.path}"
            await redis_pool.hincrby(key, 1)
            await redis_pool.expire(key, 60)
            youtube = pytube.YouTube(video_url)
            video = youtube.streams.first()
            raw_link = video.url
            app.logger.info(f'Fetched raw link for video: {video_url}')
            return redirect(raw_link)
        except pytube.exceptions.PytubeError as e:
            app.logger.error(f'Error processing video {video_url}: {str(e)}')
            return jsonify({'error': 'An error occurred while processing the video: ' + str(e)}), 500
        except Exception as e:
            app.logger.error(f'Unexpected error processing video {video_url}: {str(e)}')
            return jsonify({'error': 'An unexpected error occurred: ' + str(e)}), 500
    else:
        app.logger.warning(f'Invalid or missing video URL: {video_url}')
        return jsonify({'error': 'Invalid or missing video URL'}), 400

@app.route('/api/v1/download/', methods=['GET'])
@limiter.limit('5/minute', key_func=lambda: request.remote_addr)
def api_download():
    remote_ip = request.remote_addr
    time = now
    app.logger.info(f'{time} Request from {remote_ip} Video URL: {request.args.get("yt")}')
    video_url = request.args.get('yt', default=None, type=str).strip()
    if ((video_url and "youtube.com/watch?v=" in video_url) and video_url not in downloaded_videos):
        try:
            youtube = pytube.YouTube(video_url)
            video = youtube.streams.first()
            RemoveDownloads()
            os.makedirs(download_dir, exist_ok=True)
            filename = str(uuid.uuid4()) + '.mp4'
            video.download(download_dir, filename=filename)
            full_path = os.path.join(download_dir, filename)
            downloaded_videos.keys.append(video_url)
            downloaded_videos.values.append(filename)
            app.logger.info(f'{time} Downloaded video {video_url} to {full_path}')
            return send_file(full_path, as_attachment=True)
        except pytube.exceptions.PytubeError as e:
            app.logger.error(f'Error processing video {video_url}: {str(e)}')
            return jsonify({'error': 'An error occurred while processing the video: ' + str(e)}), 500
        except Exception as e:
            app.logger.error(f'Unexpected error downloading video {video_url}: {str(e)}')
            return jsonify({'error': 'An unexpected error occurred: ' + str(e)}), 500
    elif video_url in downloaded_videos:
        return send_file(os.path.join(download_dir, downloaded_videos[video_url]), as_attachment=True)
    else:
        app.logger.warning(f'Invalid or missing video URL: {video_url}')
        return jsonify({'error': 'Invalid or missing video URL'}), 400

@app.route('/api/v1/playlist/', methods=['GET'])
@limiter.limit('5/minute', key_func=lambda: request.remote_addr)
def api_playlist():
    playlist_url = request.args.get('yt', default=None, type=str).strip()
    if playlist_url and ("youtube.com/playlist?list=" in playlist_url):
        try:
            playlist = pytube.Playlist(playlist_url)
            download_dir = 'downloads'
            os.makedirs(download_dir, exist_ok=True)
            downloaded_files = []
            for video in playlist.videos:
                filename = str(uuid.uuid4()) + '.mp4'
                try:
                    video.streams.first().download(download_dir, filename=filename)
                    full_path = os.path.join(download_dir, filename)
                    app.logger.info(f'Downloaded video {video.title} to {full_path}')
                    downloaded_files.append(full_path)
                except pytube.exceptions.PytubeError as e:
                    app.logger.error(f'Error processing video {video.title}: {str(e)}')
                    return jsonify({'error': 'An error occurred while processing the video: ' + str(e)}), 500
                except Exception as e:
                    app.logger.error(f'Unexpected error downloading video {video.title}: {str(e)}')
                    return jsonify({'error': 'An unexpected error occurred: ' + str(e)}), 500
                finally:
                    RemoveDownloads()
            if not downloaded_files:
                return jsonify({'error': 'No video found in playlist'}), 400
            return downloaded_files
        except pytube.exceptions.PytubeError as e:
            app.logger.error(f'Error processing playlist {playlist_url}: {str(e)}')
            return jsonify({'error': 'An error occurred while processing the playlist: ' + str(e)}), 500
        except Exception as e:
            app.logger.error(f'Unexpected error downloading playlist {playlist_url}: {str(e)}')
            return jsonify({'error': 'An unexpected error occurred: ' + str(e)}), 500
    else:
        app.logger.warning(f'Invalid or missing playlist URL: {playlist_url}')
        return jsonify({'error': 'Invalid or missing playlist URL'}), 400

def get_directory_size(directory):
    return sum(os.path.getsize(f) for f in glob.glob(f'{directory}/*') if os.path.isfile(f))

def RemoveDownloads():
    downloaded_videos.clear()
    while get_directory_size('./downloads') > 4 * 1024 * 1024 * 1024:
        os.remove(sorted(glob.glob('downloads/*'), key=os.path.getctime)[0])
        app.logger.info(f'Deleted oldest temporary file: {sorted(glob.glob("downloads/*"), key=os.path.getctime)[0]}')

if __name__ == '__main__':
    print('Server started on port 15000')
    serve(app, host='0.0.0.0', port=15000)