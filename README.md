# Api

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
docker-compose up -d
python server-win.py
```

## API Documentation

### GET /api/v1/download/

params:

- yt: video url

example:

```bash
GET /api/v1/download/?yt=https://www.youtube.com/watch?v=rhwfM4u9NKw
```

### GET /api/v1/playlist/

params:

- yt: playlist url

example:

```bash
GET /api/v1/playlist/?yt=https://www.youtube.com/playlist?list=PL2-5-D-0uYy-gw8x9VK0qKY-wvzZ0b7gT
```

### GET /api/v1/

returns the raw link of the video

params:

- yt: video url (required)

example:

```bash
GET /api/v1/?yt=https://www.youtube.com/watch?v=rhwfM4u9NKw
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## Acknowledgments

* [Flask](https://github.com/pallets/flask)
* [Pytube](https://github.com/pytube/pytube)
* [Waitress](https://github.com/Pylons/waitress)
* [Logging](https://docs.python.org/3/library/logging.html#logrecord-attributes)
* [Flask Limiter](https://github.com/alisaifee/flask-limiter)
* [Redis](https://redis.io/)
* [Docker](https://www.docker.com/)
* [Docker Compose](https://docs.docker.com/compose/)
* [DragonflyDB](https://dragonflydb.io/)
