from django.urls import path

from .views import DocumentDownload

urlpatterns = [
    # Redirect request to media files to permission check.
    path('userdata/<path:relative_path>', DocumentDownload.as_view(), name='document-download'),
]
