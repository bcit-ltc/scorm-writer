#!/usr/bin/env sh

set -e

>&2 echo "make Database migrations"
python manage.py makemigrations api
echo "-------------------------------------------------------------------------------------------\n"

>&2 echo "Run Database migrations"
python manage.py migrate
echo "-------------------------------------------------------------------------------------------\n"

# Collect static files
#
>&2 echo "Collect static"
python manage.py collectstatic --noinput

>&2 echo "Starting redis"
redis-server --daemonize yes

>&2 echo "Starting Celery"
celery -A scorm_writer worker --loglevel=DEBUG --concurrency=4 -n worker1@%h --detach worker_hijack_root_logger=False worker_redirect_stdouts=True worker_redirect_stdouts_level=DEBUG
celery -A scorm_writer worker --loglevel=DEBUG --concurrency=4 -n worker2@%h --detach worker_hijack_root_logger=False worker_redirect_stdouts=True worker_redirect_stdouts_level=DEBUG
celery -A scorm_writer worker --loglevel=DEBUG --concurrency=4 -n worker3@%h --detach worker_hijack_root_logger=False worker_redirect_stdouts=True worker_redirect_stdouts_level=DEBUG
celery -A scorm_writer worker --loglevel=DEBUG --concurrency=4 -n worker4@%h --detach worker_hijack_root_logger=False worker_redirect_stdouts=True worker_redirect_stdouts_level=DEBUG

>&2 echo "Starting Gunicorn (UvicornWorker)"
exec "$@"
