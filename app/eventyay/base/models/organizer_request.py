from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from eventyay.base.models.mixins import TimestampedModel


class OrganizerRequest(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')

    name = models.CharField(max_length=200)
    email = models.EmailField()
    affiliation = models.CharField(max_length=300)
    events = models.TextField()
    organizer_name = models.CharField(max_length=200)
    slug = models.CharField(max_length=50)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_organizer_requests',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    organizer = models.ForeignKey('Organizer', null=True, blank=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='organizer_requests'
    )
    new_account = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created',)
        constraints = [
            models.UniqueConstraint(
                Lower('slug'), condition=models.Q(status='pending'), name='unique_pending_organizer_request_slug'
            ),
            models.UniqueConstraint(
                Lower('email'), condition=models.Q(status='pending'), name='unique_pending_organizer_request_email'
            ),
        ]
