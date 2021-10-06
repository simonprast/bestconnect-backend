#
# Created on Mon Nov 02 2020
#
# Copyright (c) 2020 - Simon Prast
#


from rest_framework import permissions


class ReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        print(request.user.is_staff)
        return request.user.is_staff


class OnlyShowSelf(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj == request.user
