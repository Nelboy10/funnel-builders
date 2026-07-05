from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourseViewSet, ModuleViewSet, VideoViewSet, UserProgressView

app_name = "courses"

router = DefaultRouter()
router.register(r"modules", ModuleViewSet, basename="module")
router.register(r"videos", VideoViewSet, basename="video")
router.register(r"", CourseViewSet, basename="course")

urlpatterns = [
    path("progress/", UserProgressView.as_view(), name="user_progress"),
    path("", include(router.urls)),
]
