# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""scorm_writer URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
# from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from api import views
from restapi import views

urlpatterns = [
    path('', include('api.urls')),
    path('api/', include('restapi.urls')),
    path('', views.RootPath.as_view(), name='root')
]

handler404 = 'api.views.view_404'

if settings.ADMIN_ENABLED:
    urlpatterns += [path('admin/', admin.site.urls)]

# urlpatterns += staticfiles_urlpatterns()