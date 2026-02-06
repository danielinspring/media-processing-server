# Media Processing Queue (FastAPI + Celery + FFmpeg)

This project provides an asynchronous task queue architecture for processing video, audio, and images using FastAPI, Celery, Redis, and FFmpeg. It is designed to be easily integrated with workflow automation tools like **n8n**.

## Architecture

- **API Server (FastAPI)**: Accepts job requests and returns a Job ID immediately.
- **Worker (Celery)**: Processes media files (FFmpeg) in the background.
- **Broker (Redis)**: Manages the task queue.
- **Storage**: Shared volume (`./media_storage`) for intermediate and output files.

## Prerequisites

- Docker and Docker Compose installed.

## Getting Started

1. **Start the services:**

   ```bash
   docker-compose up --build
   ```

   This will start the API server on port `8000`, the Celery worker, and Redis.

2. **Access Swagger UI:**

   Open [http://localhost:8000/docs](http://localhost:8000/docs) to view the API documentation and test endpoints.

## Usage

### 1. Submit a Job

**Endpoint:** `POST /api/v1/jobs/process-media`

**Example (cURL):**

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/jobs/process-media' \
  -H 'Content-Type: application/json' \
  -d '{
  "type": "video_convert",
  "sources": [
    "https://filesamples.com/samples/video/mp4/sample_640x360.mp4"
  ],
  "options": {
    "ffmpeg_options": {
      "vcodec": "libx264",
      "crf": 23
    }
  },
  "webhook_url": "https://your-n8n-instance.com/webhook/callback"
}'
```

### 2. Check Job Status

**Endpoint:** `GET /api/v1/jobs/{job_id}`

## n8n Integration

1. **HTTP Request Node**: Send a POST request to this API.
2. **Wait Node**: Configure it to wait for a Webhook call.
3. **Webhook Node**: This API will call your n8n Webhook URL when the processing is finished.

## Directory Structure

```
.
├── backend/
│   ├── Dockerfile
│   ├── celery_app.py
│   ├── main.py
│   ├── tasks.py
│   └── requirements.txt
├── media_storage/       # Shared volume for files
├── docker-compose.yml
└── README.md
```

## Scaling

To increase the number of workers:

```bash
docker-compose up --scale worker=3
```
