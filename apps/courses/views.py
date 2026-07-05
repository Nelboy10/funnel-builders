from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from .models import Course, Module, Video, UserProgress
from .serializers import CourseSerializer, ModuleSerializer, VideoSerializer, UserProgressSerializer
from apps.accounts.permissions import IsInstructorOrAdmin, IsInstructorOwnerOrAdmin
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Exists, OuterRef
from apps.payments.models import Purchase

class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsInstructorOrAdmin, IsInstructorOwnerOrAdmin]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category', 'level', 'status']
    search_fields = ['title', 'description']

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.select_related("category", "instructor").prefetch_related("modules__videos")
        
        if user.is_authenticated and user.role == "INSTRUCTOR":
            # Instructors see their own courses (all statuses) + published courses from others
            own_courses = qs.filter(instructor=user)
            published = qs.filter(status=Course.Status.PUBLISHED).exclude(instructor=user)
            qs = (own_courses | published).distinct()
            # Annotate purchases for access control
            qs = qs.annotate(
                is_purchased=Exists(
                    Purchase.objects.filter(
                        course=OuterRef('pk'),
                        user=user,
                        status=Purchase.Status.PAID
                    )
                )
            )
            return qs
        elif user.is_authenticated and user.role == "ADMIN":
            return qs.all()
        elif user.is_authenticated:
            # Students see only published courses
            qs = qs.filter(status=Course.Status.PUBLISHED)
            qs = qs.annotate(
                is_purchased=Exists(
                    Purchase.objects.filter(
                        course=OuterRef('pk'),
                        user=user,
                        status=Purchase.Status.PAID
                    )
                )
            )
            return qs
        else:
            return qs.filter(status=Course.Status.PUBLISHED)

    def perform_create(self, serializer):
        """Auto-assign instructor when an instructor creates a course."""
        user = self.request.user
        if user.role == "INSTRUCTOR":
            serializer.save(instructor=user)
        else:
            serializer.save()

class ModuleViewSet(viewsets.ModelViewSet):
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsInstructorOrAdmin, IsInstructorOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['course']

    def get_queryset(self):
        qs = Module.objects.all().select_related("course__instructor").prefetch_related("videos")
        user = self.request.user
        if user.is_authenticated and user.role not in ("ADMIN",):
            qs = qs.annotate(
                is_purchased=Exists(
                    Purchase.objects.filter(
                        course=OuterRef('course_id'),
                        user=user,
                        status=Purchase.Status.PAID
                    )
                )
            )
        return qs

class VideoViewSet(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsInstructorOrAdmin, IsInstructorOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['module']

    def get_queryset(self):
        qs = Video.objects.all().select_related("module__course__instructor")
        user = self.request.user
        if user.is_authenticated and user.role not in ("ADMIN",):
            qs = qs.annotate(
                is_purchased=Exists(
                    Purchase.objects.filter(
                        course=OuterRef('module__course_id'),
                        user=user,
                        status=Purchase.Status.PAID
                    )
                )
            )
        return qs

class UserProgressView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        course_id = self.request.data.get("course") or self.request.query_params.get("course")
        if not course_id:
            return None
        obj, created = UserProgress.objects.get_or_create(
            user=self.request.user,
            course_id=course_id
        )
        return obj

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if not instance:
            return Response({"error": "course ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
