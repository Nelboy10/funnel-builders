from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit objects.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'


class IsInstructorOrAdmin(permissions.BasePermission):
    """
    Allow admins full access, instructors write access, others read-only.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ('ADMIN', 'INSTRUCTOR')


class IsInstructorOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission: admins can access everything,
    instructors can only access their own courses/resources.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == 'ADMIN':
            return True
        if request.user.role == 'INSTRUCTOR':
            # Determine the course from the object
            from apps.courses.models import Course, Module, Video
            if isinstance(obj, Course):
                return obj.instructor == request.user
            elif isinstance(obj, Module):
                return obj.course.instructor == request.user
            elif isinstance(obj, Video):
                return obj.module.course.instructor == request.user
        return False

