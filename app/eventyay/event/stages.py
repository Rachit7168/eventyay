import copy
import datetime as dt

from zoneinfo import ZoneInfo

from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from eventyay.common.text.phrases import phrases
from eventyay.base.models import SubmissionStates


def _is_talks_public(event):
    if not getattr(event, 'is_public', True):
        return False
    return bool(
        getattr(event, 'talks_published', False)
        or getattr(event, 'private_testmode_talks_enabled', False)
    )


def _get_tz(event):
    tz = getattr(event, 'timezone', None) or 'UTC'
    try:
        return ZoneInfo(tz) if isinstance(tz, str) else tz
    except Exception:
        return dt.timezone.utc


def _get_event_start(event):
    date_from = getattr(event, 'date_from', None)
    if date_from:
        if isinstance(date_from, dt.datetime):
            return date_from
        elif isinstance(date_from, dt.date):
            return dt.datetime.combine(date_from, dt.time(0, 0, 0), tzinfo=_get_tz(event))
    return now()


def _get_event_end(event):
    date_to = getattr(event, 'date_to', None)
    if date_to:
        if isinstance(date_to, dt.datetime):
            if date_to.time() == dt.time(0, 0):
                return date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            return date_to
        elif isinstance(date_to, dt.date):
            return dt.datetime.combine(date_to, dt.time(23, 59, 59, 999999), tzinfo=_get_tz(event))
    return _get_event_start(event)


def _is_in_preparation(event):
    return not _is_talks_public(event) and now() <= _get_event_end(event)


def _is_cfp_open(event):
    return (
        _is_talks_public(event)
        and hasattr(event, 'cfp')
        and event.cfp.is_open
        and now() <= _get_event_end(event)
    )


def _is_in_review(event):
    return (
        not _is_cfp_open(event)
        and not _is_in_preparation(event)
        and event.submissions.filter(state=SubmissionStates.SUBMITTED).exists()
        and now() <= _get_event_start(event)
    )


def _is_in_scheduling_stage(event):
    return (
        not _is_running(event)
        and not _is_in_wrapup(event)
        and not _is_in_review(event)
        and not _is_cfp_open(event)
        and not _is_in_preparation(event)
    )


def _is_running(event):
    return _get_event_start(event) <= now() <= _get_event_end(event)


def _is_in_wrapup(event):
    return _get_event_end(event) < now()



def _is_event_configured(event):
    return bool(
        getattr(event, 'location', None)
        or getattr(event, 'email', None)
        or getattr(event, 'header_image', None)
        or getattr(event, 'logo', None)
        or (hasattr(event, 'settings') and event.settings.get('event_logo_image'))
        or getattr(event, 'landing_page_text', None)
        or getattr(event, 'primary_color', None)
    )


def _is_cfp_configured(event):
    if not hasattr(event, 'cfp') or not event.cfp:
        return False
    return bool(
        getattr(event.cfp, 'headline', None)
        or getattr(event.cfp, 'text', None)
        or getattr(event.cfp, 'deadline', None)
    )


STAGES = {
    'PREPARATION': {
        'name': _('Preparation'),
        'method': _is_in_preparation,
        'icon': 'paper-plane',
        'links': [
            {
                'title': _('Configure the event'),
                'url': ['orga_urls', 'settings'],
                'check': _is_event_configured,
            },
            {
                'title': _('Write a CfP'),
                'url': ['cfp', 'urls', 'edit_text'],
                'check': _is_cfp_configured,
            },
        ],
    },
    'CFP_OPEN': {
        'name': _('CfP is open'),
        'method': _is_cfp_open,
        'icon': 'bullhorn',
        'links': [
            {
                'title': _('Monitor proposals'),
                'url': ['orga_urls', 'submissions'],
                'check': lambda event: event.submissions.exists(),
            },
            {
                'title': _('Submit sessions for your speakers'),
                'url': ['orga_urls', 'new_submission'],
                'check': lambda event: event.submissions.exists(),
            },
            {
                'title': _('Add new speaker'),
                'url': ['orga_urls', 'new_speaker'],
                'check': lambda event: event.speakers.exists(),
            },
            {
                'title': _('Invite reviewers'),
                'url': ['organizer', 'orga_urls', 'teams'],
                'check': lambda event: event.reviewers.exists(),
            },
        ],
    },
    'REVIEW': {
        'name': _('Review'),
        'method': _is_in_review,
        'icon': 'eye',
        'links': [
            {
                'title': _('Let reviewers do their work'),
                'url': ['orga_urls', 'reviews'],
                'check': lambda event: event.reviews.exists(),
            },
            {
                'title': _('Accept or reject proposals'),
                'url': ['orga_urls', 'submissions'],
                'check': lambda event: event.submissions.filter(
                    state__in=[SubmissionStates.ACCEPTED, SubmissionStates.REJECTED]
                ).exists(),
            },
            {
                'title': _('Build your first schedule'),
                'url': ['orga_urls', 'schedule'],
                'check': lambda event: getattr(event, 'current_schedule', None) is not None
                or (getattr(event, 'wip_schedule', None) and event.wip_schedule.talks.filter(start__isnull=False).exists()),
            },
        ],
    },
    'SCHEDULE': {
        'name': phrases.schedule.schedule if phrases.schedule else _('Schedule'),
        'method': _is_in_scheduling_stage,
        'icon': 'calendar-o',
        'links': [
            {
                'title': _('Release schedules as needed'),
                'url': ['orga_urls', 'schedule'],
                'check': lambda event: getattr(event, 'current_schedule', None) is not None,
            },
            {
                'title': _('Inform your speakers about the infrastructure'),
                'url': ['orga_urls', 'compose_mails_sessions'],
                'check': lambda event: event.queued_mails.filter(sent__isnull=False).exists(),
            },
        ],
    },
    'EVENT': {
        'name': _('Event'),
        'method': _is_running,
        'icon': 'play',
        'links': [
            {
                'title': _('Provide a point of contact for the speakers'),
                'url': ['orga_urls', 'settings'],
                'check': lambda event: bool(getattr(event, 'email', None)),
            },
            {'title': _('Enjoy the event!')},
        ],
    },
    'WRAPUP': {
        'name': _('Wrapup'),
        'method': _is_in_wrapup,
        'icon': 'pause',
        'links': [
            {
                'title': _('Monitor incoming feedback'),
                'url': ['orga_urls', 'feedback'],
                'check': lambda event: event.submissions.filter(feedback__isnull=False).exists(),
            },
            {
                'title': _('Embed session recordings if available'),
                'url': ['orga_urls', 'submissions'],
                'check': lambda event: event.submissions.filter(recording_url__isnull=False).exists(),
            },
        ],
    },
}
STAGE_ORDER = ['PREPARATION', 'CFP_OPEN', 'REVIEW', 'SCHEDULE', 'EVENT', 'WRAPUP']


def in_stage(event, stage):
    return STAGES[stage]['method'](event)


def build_event_url(event, url):
    result = event
    for part in url:
        result = getattr(result, part)
    return result


def get_stages(event):
    inactive_state = 'done'
    stages = copy.deepcopy(STAGES)

    for stage in STAGES:
        is_stage_active = inactive_state == 'done' and in_stage(event, stage)
        if is_stage_active:
            inactive_state = 'todo'
        stages[stage]['phase'] = 'current' if is_stage_active else inactive_state
        for link in stages[stage].get('links', []):
            if 'check' in link:
                try:
                    link['is_configured'] = bool(link['check'](event))
                except Exception:
                    link['is_configured'] = False
            else:
                link['is_configured'] = None
            if 'url' in link and link['url']:
                link['url'] = build_event_url(event, link['url'])
    return stages

