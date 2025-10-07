import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scorm_writer.settings")
app = Celery("scorm_writer")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()