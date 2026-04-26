from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Custom pagination class for the airport service."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
