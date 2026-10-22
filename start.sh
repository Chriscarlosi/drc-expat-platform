#!/bin/sh

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Create superuser automatically if it doesn't exist
echo "Creating superuser..."
DJANGO_SUPERUSER_PASSWORD=KibaliMine2026! python manage.py createsuperuser --noinput --username admin --email admin@kibali.cd || true

# Start the web server
echo "Starting Gunicorn..."
gunicorn config.wsgi:application --bind 0.0.0.0:8000