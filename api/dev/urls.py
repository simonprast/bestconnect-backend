#
# Created on Mon Nov 02 2020
#
# Copyright (c) 2020 - Simon Prast
#


from django.urls import path, include


urlpatterns = [
    path('', include('user.api.dev.urls')),
]
