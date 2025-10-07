from django.apps import AppConfig
from django.conf import settings
import sys
import logging
logger = logging.getLogger(__name__)

class ApiV3Config(AppConfig):
    # default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        if 'runserver' in sys.argv or 'scorm_writer.asgi:application' in sys.argv:        
            logger.info("GIT_TAG: " + settings.GIT_TAG)
            logger.info("IMAGE_TAG: " + settings.IMAGE_TAG)
            logger.info("IMAGE_NAME: " + settings.IMAGE_NAME)
            if 'runserver' in sys.argv:
                logger.warning("scorm-writer has started in Dev Mode")
            else:
                logger.info("scorm-writer has started")

            from django.contrib.auth.models import User        
            if not User.objects.filter(username=settings.ADMIN_USERNAME).exists():
                User.objects.create_superuser(
                    settings.ADMIN_USERNAME, "admin@example.com", settings.ADMIN_PASSWORD
                )
                logger.info("ADMIN user created")

            from api.models import CustomToken
            theuser = User.objects.get(username=settings.ADMIN_USERNAME)
            if not CustomToken.objects.filter(user=theuser).exists():
                CustomToken.objects.create(user=theuser, key=settings.API_KEY)
                logger.info("API token added to admin user")
                