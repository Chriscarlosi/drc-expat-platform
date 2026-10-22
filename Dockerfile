# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Prevents interactive prompts during apt-get install
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
# Added --allow-releaseinfo-change and apt-get clean to fix timing/download issues
RUN apt-get update --allow-releaseinfo-change && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    python3-dev \
    musl-dev \
    libjpeg-dev \
    zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Run the application with Gunicorn
RUN chmod +x start.sh
CMD ["./start.sh"]