FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN pip install --no-cache-dir flask yt-dlp youtube-transcript-api

COPY . .

EXPOSE 8000

CMD ["python", "web_app.py"]