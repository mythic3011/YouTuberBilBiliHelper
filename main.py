import asyncio
import uuid
import os
from fastapi import FastAPI, WebSocket, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from collections import defaultdict
import aiohttp
import yt_dlp
import time
from urllib.parse import urlparse
<<<<<<< HEAD
import logging
import redis.asyncio as redis
=======
import logging
import redis.asyncio as redis
import uvicorn
>>>>>>> e7199fc7509c4bdc56ab89cb65e0ef65dcce1267

app = FastAPI()

# Configuration (environment variables or config file)
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", 60))  # seconds
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", 100))
DOWNLOAD_DIRECTORY = os.environ.get("DOWNLOAD_DIRECTORY", "downloads")
MAX_STORAGE_GB = int(os.environ.get("MAX_STORAGE_GB", 10))
MAX_STORAGE_BYTES = MAX_STORAGE_GB * 1024 * 1024 * 1024

# Logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

def is_youtube_url(url: str) -> bool:
    parsed_url = urlparse(url)
    return parsed_url.netloc in ["www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"]

def is_bilibili_url(url: str) -> bool:
    parsed_url = urlparse(url)
    return parsed_url.netloc in ["www.bilibili.com", "bilibili.com"]

async def apply_rate_limit(request: Request):
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    now = int(time.time())
    with await redis_client.pipeline() as pipe:
        await pipe.zadd(key, {now: now})
        await pipe.zremrangebyscore(key, 0, now - RATE_LIMIT_WINDOW)
        count_future = pipe.zcard(key)
        await pipe.expire(key, RATE_LIMIT_WINDOW)
        request_count = await count_future
    if request_count > RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests")

async def get_downloaded_files_size():
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(DOWNLOAD_DIRECTORY):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except OSError as e:
                logging.warning(f"Could not get size of file {fp}: {e}")
    return total_size

async def enforce_storage_limit():
    current_size = await get_downloaded_files_size()
    if current_size > MAX_STORAGE_BYTES:
        logging.warning(
            f"Storage limit exceeded. Current size: {current_size / (1024**3):.2f} GB, Limit: {MAX_STORAGE_GB} GB"
        )
        # Simple logic to delete oldest files
        files = []
        for dirpath, dirnames, filenames in os.walk(DOWNLOAD_DIRECTORY):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    files.append((filepath, os.path.getmtime(filepath)))
                except OSError as e:
                    logging.warning(f"Could not get modification time of file {filepath}: {e}")

        files.sort(key=lambda item: item[1])

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
            except OSError as e:
                logging.error(f"Error deleting file {filepath}: {e}")

async def fetch_video_info(url: str):
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logging.error(f"HTTPException: {exc.detail} (status_code={exc.status_code})")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unexpected error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})

@app.post("/youtube/download/")
async def download_youtube_video(request: Request, url: str,  rate_limit: None = Depends(apply_rate_limit)):
    if not is_youtube_url(url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    try:
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_DIRECTORY, 'youtube', '%(title)s.%(ext)s'),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        await enforce_storage_limit()
        return {"message": "YouTube video download started"}
    except Exception as e:
        logging.error(f"Error downloading YouTube video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download YouTube video: {str(e)}")

@app.post("/bilibili/download/")
async def download_bilibili_video(request: Request, url: str, rate_limit: None = Depends(apply_rate_limit)):
    if not is_bilibili_url(url):
        raise HTTPException(status_code=400, detail="Invalid Bilibili URL")
    try:
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_DIRECTORY, 'bilibili', '%(title)s.%(ext)s'),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        await enforce_storage_limit()
        return {"message": "Bilibili video download started"}
    except Exception as e:
        logging.error(f"Error downloading Bilibili video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download Bilibili video: {str(e)}")

@app.get("/youtube/stream/")
async def stream_youtube_video(request: Request, url: str, rate_limit: None = Depends(apply_rate_limit)):
    if not is_youtube_url(url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    try:
        info_dict = await fetch_video_info(url)
        if info_dict and 'url' in info_dict:
            async with aiohttp.ClientSession() as session:
                async with session.get(info_dict['url']) as response:
                    if response.status == 200:
                        return StreamingResponse(response.content, media_type=response.headers.get('content-type'))
                    else:
                        raise HTTPException(status_code=response.status, detail="Failed to fetch video stream")
        else:
            raise HTTPException(status_code=404, detail="Could not retrieve video stream URL")
    except Exception as e:
        logging.error(f"Error streaming YouTube video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stream YouTube video: {str(e)}")

@app.get("/bilibili/stream/")
async def stream_bilibili_video(request: Request, url: str, rate_limit: None = Depends(apply_rate_limit)):
    if not is_bilibili_url(url):
        raise HTTPException(status_code=400, detail="Invalid Bilibili URL")
    try:
        info_dict = await fetch_video_info(url)
        if info_dict and 'url' in info_dict:
            async with aiohttp.ClientSession() as session:
                async with session.get(info_dict['url']) as response:
                    if response.status == 200:
                        return StreamingResponse(response.content, media_type=response.headers.get('content-type'))
                    else:
                        raise HTTPException(status_code=response.status, detail="Failed to fetch video stream")
        else:
            raise HTTPException(status_code=404, detail="Could not retrieve video stream URL")
    except Exception as e:
        logging.error(f"Error streaming Bilibili video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stream Bilibili video: {str(e)}")

# оставлен функционал websocket из первого кода, предполагая, что он нужен
class AppState:
    def __init__(self):
        self.rooms = defaultdict(set)

    def add_client(self, room_id: str, client_id: str):
        self.rooms[room_id].add(client_id)

    def remove_client(self, room_id: str, client_id: str):
        if client_id in self.rooms[room_id]:
            self.rooms[room_id].remove(client_id)
            if not self.rooms[room_id]:
                del self.rooms[room_id]

    def get_clients(self, room_id: str):
        return self.rooms.get(room_id, set())

video_app_state = AppState()

async def ws_handler(websocket: WebSocket):
    client_id = str(uuid.uuid4())
    room_id = "default"
    video_app_state.add_client(room_id, client_id)
    try:
<<<<<<< HEAD
        await websocket.accept()
        while True:
            data = await websocket.receive_text()
            clients = video_app_state.get_clients(room_id)
            for other_client_id in clients:
                if other_client_id != client_id:
                    await websocket.send_text(f"User {client_id} says: {data}")
=======
        await websocket.accept()
        while True:
            data = await websocket.receive_text()
            clients = video_app_state.get_clients(room_id)
            for other_client_id in clients:
                if other_client_id != client_id:
                    # Here we send the message directly to the WebSocket, not via HTTP
                    await websocket.send_text(f"User {client_id} says: {data}")
>>>>>>> e7199fc7509c4bdc56ab89cb65e0ef65dcce1267
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        video_app_state.remove_client(room_id, client_id)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_handler(websocket)

if __name__ == "__main__":
<<<<<<< HEAD
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
=======
    uvicorn.run(app, host="0.0.0.0", port=8000)

>>>>>>> e7199fc7509c4bdc56ab89cb65e0ef65dcce1267