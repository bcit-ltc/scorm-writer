# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from .serializers import JsonToScormSerializer, QuestionLibraryPackageSerializer
from rest_framework.views import APIView
from django.http import FileResponse, JsonResponse
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import JSONParser


from django.conf import settings


import logging
logger = logging.getLogger(__name__)
from .logging.contextfilter import QuestionlibraryFilenameFilter
loggingfilter = QuestionlibraryFilenameFilter()
logger.addFilter(loggingfilter)

class TokenAuthenticationWithBearer(TokenAuthentication):
    keyword = 'Bearer'

    def __init__(self):
        super(TokenAuthenticationWithBearer, self).__init__()

class JsonToScorm(APIView):
    parser_classes = [JSONParser]
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthenticationWithBearer]
    serializer_class = JsonToScormSerializer

    def post(self, request, format=None):

        json_data = request.data
        ql_serializer = QuestionLibraryPackageSerializer(data=json_data['data'])
        if ql_serializer.is_valid():
            ql_instance = ql_serializer.save()
            ql_instance.filter_main_title()
            ql_instance.folder_path = settings.MEDIA_ROOT + str(ql_instance.id)
            ql_instance.image_path = ql_instance.folder_path + settings.MEDIA_URL
            ql_instance.create_directory()
            ql_instance.save()
            file_name = ql_instance.filtered_main_title
            # if (ql_instance.total_question_errors + ql_instance.total_document_errors == 0):
            ql_instance.create_xml_files()
            ql_instance.zip_files()
            file_response = FileResponse(ql_instance.zip_file)
            file_response['Content-Disposition'] = 'attachment; filename="' + file_name + '"'
            logger.addFilter(QuestionlibraryFilenameFilter(ql_instance))
            logger.info("[" + str(ql_instance.id) + "] " +">>>>>>>>>>Transaction Finished>>>>>>>>>>")

            ql_instance.cleanup()

            return file_response
                
        return JsonResponse({"hostname": settings.GIT_TAG, "serializer_errors": ql_serializer.errors}, status=400)

class RootPath(APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        from .models import StatusResponse
        from .serializers import StatusResponseSerializer

        status = StatusResponse(version_number=settings.GIT_TAG)
        serializer = StatusResponseSerializer(status)

        return JsonResponse(serializer.data,
                            json_dumps_params={'indent': 2},
                            status=200)


from django.shortcuts import redirect


def view_404(request, exception=None):
    return redirect('/')


def redirect_view(request, namespace, name, slug, actualurl):
    print(slug)
    print(actualurl)
    return redirect('/' + actualurl)
    # return None


def redirect_root(request, namespace, name, slug):
    print(slug)
    return redirect('/')
