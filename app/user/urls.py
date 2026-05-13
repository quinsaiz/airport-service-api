from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from user.views import CreateUserView, GitHubLoginView, GoogleLoginView, ManageUserView, VerifyEmailView

urlpatterns = [
    path("register/", CreateUserView.as_view(), name="create"),
    path("verify-email/<str:token>/", VerifyEmailView.as_view(), name="verify-email"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("google-login/", GoogleLoginView.as_view(), name="google_login"),
    path("github-login/", GitHubLoginView.as_view(), name="github_login"),
    path("me/", ManageUserView.as_view(), name="manage"),
]

app_name = "user"
