"""francy URL Configuration

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
import sys

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db.utils import OperationalError
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from graphene_django.views import GraphQLView

from user.default_superuser import create_admin_user


urlpatterns = [
    path('admin/', admin.site.urls),

    # GraphQL API
    path('graphql', csrf_exempt(GraphQLView.as_view(graphiql=settings.DEBUG))),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Check command line paramters used when starting the app for Django's 'migrate' keyword.
if 'migrate' not in sys.argv:
    try:
        create_admin_user()
    except OperationalError:
        print('COULD NOT CREATE ADMIN USER (is there an un-migrated field on the user model?)')
