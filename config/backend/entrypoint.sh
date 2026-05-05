#!/bin/sh

echo "Waiting for database..."
python wait_for_db.py

echo "Applying migrations..."
python manage.py migrate

echo "Starting server..."
python manage.py runserver 0.0.0.0:8000