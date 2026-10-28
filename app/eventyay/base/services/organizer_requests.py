import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from eventyay.base.forms.organizer_request import validate_request_slug
from eventyay.base.models import Organizer, OrganizerRequest, User
from eventyay.base.services.mail import SendMailException, mail
from eventyay.base.services.organizer_creation import create_core_team


logger = logging.getLogger(__name__)


def absolute_url(path: str) -> str:
    return settings.SITE_URL.rstrip('/') + path


def notify(email: str, subject: str, body: str) -> None:
    try:
        mail(email, subject, 'pretixcontrol/email/organizer_request.txt', {'body': body})
    except SendMailException:
        logger.exception('Could not send organiser request notification')


def notify_submission(application: OrganizerRequest) -> None:
    notify(
        application.email,
        _('Organiser request received'),
        _('Thank you for your request. We will review it within a few business days.'),
    )
    review_url = absolute_url(reverse('eventyay_admin:admin.organizer_requests.detail', args=[application.pk]))
    body = _(
        'A new organiser request is ready for review.\n\nName: {name}\nEmail: {email}\n'
        'Affiliation: {affiliation}\nEvents: {events}\nOrganiser name: {organizer_name}\nShort '
        'form: {slug}\n\nReview: {url}'
    ).format(
        name=application.name,
        email=application.email,
        affiliation=application.affiliation,
        events=application.events,
        organizer_name=application.organizer_name,
        slug=application.slug,
        url=review_url,
    )
    for email in User.objects.filter(
        Q(is_staff=True) | Q(is_superuser=True), is_active=True, is_spam=False
    ).values_list('email', flat=True):
        notify(email, _('New organiser request'), body)


@transaction.atomic
def review_request(
    pk: int, reviewer: User, *, approve: bool, organizer_name: str = '', slug: str = '', reason: str = ''
) -> OrganizerRequest:
    application = OrganizerRequest.objects.select_for_update().get(pk=pk)
    if application.status != OrganizerRequest.Status.PENDING:
        raise ValidationError(_('This request has already been reviewed.'))
    if approve:
        validate_request_slug(slug)
        user = User.objects.filter(email__iexact=application.email).first()
        if user and (not user.is_active or user.is_spam):
            raise ValidationError(_('This account is inactive or marked as spam and cannot be granted access.'))
        application.new_account = user is None
        if user is None:
            user = User.objects.create_user(email=application.email, fullname=application.name)
        organizer = Organizer(name=organizer_name, slug=slug)
        organizer.full_clean()
        organizer.save()
        create_core_team(organizer, user)
        if not user.default_organizer_id:
            user.default_organizer = organizer
            user.save(update_fields=['default_organizer'])
        application.organizer_name = organizer_name
        application.slug = slug
        application.organizer = organizer
        application.user = user
        application.status = OrganizerRequest.Status.APPROVED
        url = absolute_url(reverse('control:organizer', kwargs={'organizer': slug}))
        if application.new_account:
            params = urlencode({'id': user.pk, 'token': default_token_generator.make_token(user)})
            setup_url = absolute_url(reverse('eventyay_common:auth.forgot.recover')) + '?' + params
            body = _(
                'Welcome to Eventyay! Your request for the organiser "{name}" has been approved.\n\n'
                'We have created an Eventyay account for {email} and added it to your organiser’s '
                'Core Organizing Team.\n\n'
                'Set your password: {url}\n\n'
                'Open this link, enter your new password twice, and select "Set password and continue". '
                'You will be signed in automatically and taken to your organiser dashboard, '
                'where you can create your first event.\n\n'
                'This link expires after {hours} hours. If it expires, request another using '
                '"Forgot password" on the login page.\n\nYour organiser: {organizer_url}'
            ).format(
                name=organizer_name,
                email=user.email,
                url=setup_url,
                hours=settings.PASSWORD_RESET_TIMEOUT // 3600,
                organizer_url=url,
            )
        else:
            body = _(
                'Your request for the organiser "{name}" has been approved.\n\n'
                'Your existing Eventyay account ({email}) has been added to its Core Organizing Team.\n\n'
                'Open your organiser: {url}\n\n'
                'If prompted, sign in with your existing Eventyay account. From the organiser dashboard, '
                'you can create your first event. You do not need to create a new account or set a new password.'
            ).format(name=organizer_name, email=user.email, url=url)
        subject = _('Your organiser request has been approved')
    else:
        application.status = OrganizerRequest.Status.REJECTED
        application.reason = reason
        subject = _('Your organiser request has been rejected')
        body = _('Your organiser request has been rejected.')
        if reason:
            body += '\n\n' + _('Reason: {reason}').format(reason=reason)
    application.reviewed_by = reviewer
    application.reviewed_at = timezone.now()
    application.save()
    transaction.on_commit(lambda: notify(application.email, subject, body))
    return application
