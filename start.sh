#!/bin/sh

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Start the web server
echo "Starting Gunicorn..."
gunicorn config.wsgi:application --bind 0.0.0.0:8000