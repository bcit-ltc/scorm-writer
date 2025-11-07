# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
ASGI config for scorm_writer project.

Exposes the ASGI callable as a module-level variable named ``application``.
HTTP-only (no WebSocket routing).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scorm_writer.settings')

application = get_asgi_application()
