"""Helpers for the new-user onboarding dashboard."""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.http import HttpRequest
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_scopes import scopes_disabled

from eventyay.base.models import Event, Order, Submission, User
from eventyay.helpers.daterange import daterange
from eventyay.multidomain.urlreverse import eventreverse

RECOMMENDED_EVENTS_LIMIT = 6


def user_has_orders(user: User) -> bool:
    if not user.email:
        return False
    with scopes_disabled():
        return Order.objects.filter(email__iexact=user.email).exists()


def user_has_sessions_or_proposals(user: User) -> bool:
    if not user.email:
        return False
    with scopes_disabled():
        return Submission.objects.filter(speakers__email__iexact=user.email).exists()


def user_has_organised_events(user: User, request: HttpRequest | None = None) -> bool:
    with scopes_disabled():
        return user.get_events_with_any_permission(request).exists()


def user_needs_onboarding(user: User, request: HttpRequest | None = None) -> bool:
    """Return True when the user has no personal Eventyay activity yet."""
    if user_has_orders(user):
        return False
    if user_has_sessions_or_proposals(user):
        return False
    if user_has_organised_events(user, request):
        return False
    return True


def is_profile_incomplete(user: User) -> bool:
    """Account profile is incomplete without a display name or photo."""
    has_name = bool((user.fullname or '').strip())
    has_photo = bool(user.has_profile_picture)
    return not (has_name and has_photo)


def _public_upcoming_events_qs():
    today = now().replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        Event.objects.select_related('organizer')
        .prefetch_related('_settings_objects', 'cfp')
        .filter(live=True, is_public=True, testmode=False)
        .filter(Q(startpage_visible=True) | Q(startpage_featured=True))
        .filter(Q(date_to__gte=today) | Q(date_to__isnull=True, date_from__gte=today))
        .exclude(_settings_objects__key='talks_testmode', _settings_objects__value='True')
        .order_by('-startpage_featured', 'date_from')
    )


def _event_date_range(event: Event) -> str:
    tzname = event.settings.get('timezone') or event.timezone or 'UTC'
    tz = ZoneInfo(str(tzname))
    if event.has_subevents:
        return str(_('Event series'))
    if event.date_to:
        return daterange(event.date_from.astimezone(tz), event.date_to.astimezone(tz))
    return event.get_date_range_display()


def _event_location_label(event: Event) -> str:
    location = str(event.location or '').strip()
    if location:
        # Keep the first line for compact cards.
        return location.splitlines()[0]
    tzname = event.settings.get('timezone') or event.timezone
    if tzname:
        return str(tzname)
    return ''


def _event_cfp_is_open(event: Event) -> bool:
    from eventyay.base.models.cfp import CfP

    try:
        cfp = event.cfp
    except CfP.DoesNotExist:
        return False
    return bool(cfp.is_open)


def _event_badges(event: Event) -> list[dict[str, str]]:
    badges: list[dict[str, str]] = []
    if event.presale_is_running:
        badges.append({'label': str(_('Tickets on sale')), 'tone': 'success'})
    if _event_cfp_is_open(event):
        badges.append({'label': str(_('Call for proposals')), 'tone': 'accent'})
    return badges


def _event_primary_action(event: Event) -> dict[str, str]:
    url = eventreverse(event, 'presale:event.index')
    if _event_cfp_is_open(event) and not event.presale_is_running:
        return {'label': str(_('Submit proposal')), 'url': url}
    if event.presale_is_running:
        return {'label': str(_('Register')), 'url': url}
    return {'label': str(_('View event')), 'url': url}


def build_recommended_event_cards(limit: int = RECOMMENDED_EVENTS_LIMIT) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    with scopes_disabled():
        for event in _public_upcoming_events_qs()[:limit]:
            if event.has_component_testmode:
                continue
            cards.append(
                {
                    'name': str(event.name),
                    'url': eventreverse(event, 'presale:event.index'),
                    'image_url': event.preview_image_url_with_fallback or '',
                    'date_range': _event_date_range(event),
                    'location': _event_location_label(event),
                    'badges': _event_badges(event),
                    'primary_action': _event_primary_action(event),
                }
            )
    return cards


def build_onboarding_context(request: HttpRequest) -> dict[str, Any]:
    user = request.user
    can_create_event = user.teams.filter(can_create_events=True).exists()
    profile_incomplete = is_profile_incomplete(user)
    return {
        'is_onboarding_dashboard': True,
        'can_create_event': can_create_event,
        'profile_incomplete': profile_incomplete,
        'recommended_events': build_recommended_event_cards(),
        'browse_events_url': reverse('presale:index'),
        'upcoming_events_url': reverse('presale:events.upcoming'),
        'open_calls_url': reverse('presale:events.upcoming') + '?cfp=open',
        'create_event_url': reverse('eventyay_common:events.add'),
        'edit_profile_url': reverse('eventyay_common:account.general'),
        'search_events_url': reverse('presale:index'),
    }
