from django.conf import settings
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views import View

from .models import Document


class DocumentDownload(View):
    def get(self, request, relative_path):
        # get_object_or_404:
        # Calls get() on a given model manager, but it raises Http404 instead of the model’s DoesNotExist exception.
        document = get_object_or_404(Document, file=relative_path)

        # Deny file access if the reuqesting user is not authorized to do so.
        # TODO: Implement files with group access
        if request.user.is_anonymous or (not request.user.is_admin and document.owner != request.user):
            return HttpResponseForbidden()

        absolute_path = '{}/{}'.format(settings.USERDATA_ROOT, relative_path)

        # Use as_attachment=True to download the file instead of showing it in-browser.
        response = FileResponse(open(absolute_path, 'rb'), as_attachment=True)
        return response
