import os
import requests
import ffmpeg
import logging
import shutil
from pathlib import Path
from celery_app import celery_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Shared volume path
DATA_DIR = Path("/data")

@celery_app.task(bind=True, name="tasks.process_media")
def process_media(self, job_type: str, sources: list, options: dict, webhook_url: str):
    """
    Celery task to process media files using FFmpeg.
    """
    job_id = self.request.id
    logger.info(f"Starting job {job_id} | Type: {job_type}")

    # Create a unique directory for this job
    job_dir = DATA_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    input_files = []
    output_filename = f"output_{job_id}.mp4"
    output_path = job_dir / output_filename

    try:
        # 1. Download Sources
        for idx, source in enumerate(sources):
            if source.startswith("http"):
                local_filename = job_dir / f"input_{idx}.mp4"
                logger.info(f"Downloading source {idx+1}/{len(sources)}: {source}")
                download_file(source, local_filename)
                input_files.append(local_filename)
            else:
                logger.warning(f"Skipping non-http source: {source}")

        if not input_files:
            raise ValueError("No valid input files provided.")

        # 2. Process with FFmpeg
        logger.info("Starting FFmpeg processing...")

        if job_type == "video_merge":
            # Concatenate all input videos
            inputs = [ffmpeg.input(str(f)) for f in input_files]
            # concat filter (v=1, a=1 ensures both video and audio are passed)
            stream = ffmpeg.concat(*inputs, v=1, a=1)
            stream = ffmpeg.output(stream, str(output_path), **options.get("ffmpeg_options", {}))
            ffmpeg.run(stream, overwrite_output=True)

        elif job_type == "image_resize":
            # Example for images (using ffmpeg or PIL, but sticking to ffmpeg here as requested)
            # This is just a placeholder example
            stream = ffmpeg.input(str(input_files[0]))
            # strict simple resize
            resolution = options.get("resolution", "1920x1080")
            stream = ffmpeg.output(stream, str(output_path), s=resolution)
            ffmpeg.run(stream, overwrite_output=True)

        else:
            # Default: Convert/Copy first file
            stream = ffmpeg.input(str(input_files[0]))
            stream = ffmpeg.output(stream, str(output_path), **options.get("ffmpeg_options", {}))
            ffmpeg.run(stream, overwrite_output=True)

        logger.info(f"FFmpeg processing complete. Output: {output_path}")

        # 3. Webhook Callback
        # In a real scenario, you might upload 'output_path' to S3 here and get a presigned URL.
        # For this local demo, we'll assume the path is accessible or send the path.

        result_data = {
            "job_id": job_id,
            "status": "completed",
            "output_path": str(output_path),
            "info": "File is located in shared volume"
        }

        if webhook_url:
            logger.info(f"Sending webhook to {webhook_url}")
            try:
                requests.post(webhook_url, json=result_data, timeout=10)
            except requests.RequestException as e:
                logger.error(f"Failed to call webhook: {e}")

        return result_data

    except Exception as e:
        logger.error(f"Job failed: {e}")
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e)
                }, timeout=10)
            except:
                pass
        raise e # Re-raise to mark task as failed in Celery

    finally:
        # 4. Cleanup
        # Remove input files to save space
        logger.info("Cleaning up input files...")
        for f in input_files:
            if f.exists():
                try:
                    f.unlink()
                except Exception as cleanup_error:
                    logger.warning(f"Failed to delete {f}: {cleanup_error}")

        # Note: We are keeping the output file and the directory for now.
        # In production, you might want a separate cleanup policy or upload-then-delete.

def download_file(url, path):
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
