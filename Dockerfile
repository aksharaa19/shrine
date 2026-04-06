FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

WORKDIR /app/backend
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]