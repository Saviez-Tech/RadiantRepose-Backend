from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    Custom permission to only allow users in the 'Administrators' group to access the view.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name='Administrator').exists() 