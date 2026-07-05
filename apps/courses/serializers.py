from rest_framework import serializers
from .models import Course, Module, Video, UserProgress

def _check_access(instance, user):
    has_access = False
    if user and user.is_authenticated:
        if user.role == "ADMIN":
            has_access = True
        else:
            # Determine course depending on the instance type
            course_obj = None
            if isinstance(instance, Course):
                course_obj = instance
            elif hasattr(instance, 'course'):
                course_obj = getattr(instance, 'course')
            elif hasattr(instance, 'module') and hasattr(instance.module, 'course'):
                course_obj = getattr(instance.module, 'course')
                
            # If the user is the instructor of the course, they have full access
            if course_obj and getattr(course_obj, 'instructor_id', None) == user.id:
                has_access = True
            else:
                # Check if annotated 'is_purchased' exists (from ViewSets)
                if hasattr(instance, "is_purchased"):
                    has_access = instance.is_purchased
                elif hasattr(instance, "module") and hasattr(instance.module.course, "is_purchased"):
                    has_access = instance.module.course.is_purchased
                elif hasattr(instance, "course") and hasattr(instance.course, "is_purchased"):
                    has_access = instance.course.is_purchased
                else:
                    # Fallback to direct DB query if annotation is missing (should not happen in normal API flow)
                    from apps.payments.models import Purchase
                    if course_obj:
                        has_access = Purchase.objects.filter(user=user, course=course_obj, status=Purchase.Status.PAID).exists()
    return has_access

class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ("id", "title", "description", "video_file", "youtube_url", "thumbnail", "duration", "order", "free_preview", "module")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get("request")
        user = request.user if request else None
        
        has_access = _check_access(instance, user)
        if not has_access and not instance.free_preview:
            representation["video_file"] = None
            representation["youtube_url"] = None
            
        return representation

class ModuleSerializer(serializers.ModelSerializer):
    videos = VideoSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ("id", "title", "description", "order", "videos", "course")

class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ("id", "title", "slug", "description", "thumbnail", "price", "category", "total_duration", "level", "status", "instructor", "created_at", "updated_at", "modules")
        read_only_fields = ("instructor",)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get("request")
        user = request.user if request else None
        
        has_access = _check_access(instance, user)
        if not has_access:
            representation["modules"] = []
            
        return representation

class UserProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProgress
        fields = ("course", "last_watched_video", "position_in_seconds", "progress_percentage", "updated_at")
        read_only_fields = ("updated_at",)
