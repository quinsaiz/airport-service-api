from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request
from rest_framework.views import View


class IsAdminOrReadOnly(BasePermission):
    """
    Allows GET, HEAD, and OPTIONS requests for any user.
    POST, PUT, PATCH, and DELETE requests are restricted to administrators.
    """

    def has_permission(self, request: Request, view: View) -> bool:
        return bool(
            request.method in SAFE_METHODS or (request.user and request.user.is_staff)
        )
