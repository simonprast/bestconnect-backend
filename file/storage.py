import os
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.functional import cached_property


# Override the base location and url properties for Django's default file system.
# The default FileSystemStorage class uses the MEDIA_ROOT/MEDIA_URL values for storing any uploaded content.
class UserDataFileStorage(FileSystemStorage):
    @cached_property
    def base_location(self):
        return self._value_or_setting(self._location, settings.USERDATA_ROOT)

    @cached_property
    def base_url(self):
        if self._base_url is not None and not self._base_url.endswith('/'):
            self._base_url += '/'
        return self._value_or_setting(self._base_url, settings.USERDATA_URL)


def create_file_path(instance, filename):
    # Uses the User's identification and a unique uuid string for creating the file's location.
    folder = str(instance.owner.id) + '/' + str(uuid.uuid4())
    return os.path.join(folder, filename)
