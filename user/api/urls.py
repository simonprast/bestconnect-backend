#
# Created on Mon Nov 02 2020
#
# Copyright (c) 2020 - Simon Prast
#


from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.urlpatterns import format_suffix_patterns

from . import api_views

urlpatterns = [
    path('users/', api_views.UserList.as_view()),
    path('users/<int:pk>/', api_views.UserDetail.as_view()),
    path('users/create/', api_views.UserCreateOrLogin.as_view()),

    # Todo:
    # https://stackoverflow.com/questions/14567586/token-authentication-for-restful-api-should-the-token-be-periodically-changed
    path('auth/', obtain_auth_token, name='api_token_auth'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
