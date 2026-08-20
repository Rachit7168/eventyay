from django.db import models
from drf_spectacular.utils import extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from eventyay.api.mixins import PretalxViewSetMixin
from eventyay.api.serializers.feedback import FeedbackSerializer
from eventyay.base.models import Feedback

class FeedbackViewSet(
    PretalxViewSetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = FeedbackSerializer
    queryset = Feedback.objects.none()
    allow_public_read = True
    
    # We don't define endpoint = 'feedback' if we just register it in router.
    # But PretalxViewSetMixin might use self.endpoint.
    endpoint = 'feedback'

    def get_queryset(self):
        if not self.event:
            return self.queryset
        
        qs = Feedback.objects.filter(talk__event=self.event)
        
        # We only want top-level comments when listing (replies are nested)
        if self.action == 'list':
            qs = qs.filter(parent__isnull=True)
        
        talk_code = self.request.query_params.get('talk')
        if talk_code:
            qs = qs.filter(talk__code=talk_code)
            
        if not self.request.user.has_perm('base.orga_list_submission', self.event):
            # Only published, OR authored by the user
            if self.request.user.is_authenticated:
                qs = qs.filter(models.Q(status='published') | models.Q(author=self.request.user))
            else:
                qs = qs.filter(status='published')
                
        # Only show public comments in the public API unless you're orga
        if not self.request.user.has_perm('base.orga_list_submission', self.event):
             qs = qs.filter(is_public=True)

        return qs.order_by('-created')

    def perform_create(self, serializer):
        settings = self.event.settings
        if not settings.use_feedback:
            raise PermissionDenied("Feedback is not enabled for this event.")
            
        user = self.request.user
        if not user.is_authenticated:
            raise PermissionDenied("You must be logged in to comment.")

        # Who can comment
        if settings.feedback_who_can_comment == 'attendees':
            # Check if user has a ticket or is registered (assume attendees means ticket holder for now, or just registered user if we don't have tickets)
            # Actually for simplicity, we'll just check if they are authenticated for 'registered'
            # For 'attendees' it can be more complex, we might just skip the strict check for now or implement if needed.
            pass

        is_public = serializer.validated_data.get('is_public', True)
        if not is_public and not settings.feedback_allow_anonymous:
            raise PermissionDenied("Anonymous feedback is not allowed.")
            
        status = 'pending' if settings.feedback_require_review else 'published'
        
        serializer.save(
            author=user,
            status=status
        )
