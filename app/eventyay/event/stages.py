import copy

from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from eventyay.common.text.phrases import phrases
from eventyay.base.models import SubmissionStates


def _is_in_preparation(event):
    return not event.is_public and now() <= event.date_from


def _is_cfp_open(event):
    return not _is_in_preparation(event) and event.cfp.is_open


def _is_in_review(event):
    return (
        not _is_cfp_open(event)
        and event.submissions.filter(state=SubmissionStates.SUBMITTED).exists()
        and now() <= event.date_from
    )


def _is_in_scheduling_stage(event):
    return not _is_running(event) and not _is_in_wrapup(event) and not _is_in_review(event)


def _is_running(event):
    return event.date_from <= now() <= event.date_to


def _is_in_wrapup(event):
    return event.date_to <= now()


STAGES = {
    'PREPARATION': {
        'name': _('Preparation'),
        'method': _is_in_preparation,
        'icon': 'paper-plane',
        'links': [
            {'title': _('Configure the event'), 'url': ['orga_urls', 'settings']},
            {'title': _('Gather your team'), 'url': ['organizer', 'orga_urls', 'base']},
            {'title': _('Write a CfP'), 'url': ['cfp', 'urls', 'edit_text']},
            {
                'title': _('Customize mail templates'),
                'url': ['orga_urls', 'mail_templates'],
            },
        ],
    },
    'CFP_OPEN': {
        'name': _('CfP is open'),
        'method': _is_cfp_open,
        'icon': 'bullhorn',
        'links': [
            {'title': _('Monitor proposals'), 'url': ['orga_urls', 'submissions']},
            {
                'title': _('Submit sessions for your speakers'),
                'url': ['orga_urls', 'new_submission'],
            },
            {'title': _('Invite reviewers'), 'url': ['organizer', 'orga_urls', 'base']},
        ],
    },
    'REVIEW': {
        'name': _('Review'),
        'method': _is_in_review,
        'icon': 'eye',
        'links': [
            {'title': _('Let reviewers do their work')},
            {
                'title': _('Accept or reject proposals'),
                'url': ['orga_urls', 'submissions'],
            },
            {'title': _('Build your first schedule'), 'url': ['orga_urls', 'schedule']},
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
            },
            {
                'title': _('Inform your speakers about the infrastructure'),
                'url': ['orga_urls', 'compose_mails_sessions'],
            },
        ],
    },
    'EVENT': {
        'name': ngettext_lazy('Event', 'Events', 1),
        'method': _is_running,
        'icon': 'play',
        'links': [
            {'title': _('Provide a point of contact for the speakers')},
            {'title': _('Enjoy the event!')},
        ],
    },
    'WRAPUP': {
        'name': _('Wrapup'),
        'method': _is_in_wrapup,
        'icon': 'pause',
        'links': [
            {'title': _('Monitor incoming feedback')},
            {'title': _('Embed session recordings if available')},
            {'title': _('Release next event date?')},
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
            if 'url' in link and link['url']:
                link['url'] = build_event_url(event, link['url'])
    return stages


def get_workflow_steps(event):
    """Build a 7-step labeled workflow for the redesigned talks dashboard.

    Each step: {label, status, summary, phase, icon, url}
    phase is one of: 'done', 'active', 'pending', 'issue'
    """
    from django.utils.timezone import now
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import ngettext_lazy
    from eventyay.base.models import SubmissionStates

    submitted_count = event.submissions.filter(state=SubmissionStates.SUBMITTED).count()
    accepted_count = event.submissions.filter(state=SubmissionStates.ACCEPTED).count()
    confirmed_count = event.submissions.filter(state=SubmissionStates.CONFIRMED).count()
    rejected_count = event.submissions.filter(state=SubmissionStates.REJECTED).count()
    talk_count = event.talks.count()
    unscheduled_count = confirmed_count - talk_count if confirmed_count > talk_count else 0
    total_processed = accepted_count + confirmed_count + rejected_count

    # 1. Call for proposals
    is_cfp_open = event.cfp.is_open if hasattr(event, 'cfp') else False
    if is_cfp_open:
        cfp_phase = 'active'
        cfp_status = _('Open')
    elif submitted_count + total_processed > 0:
        cfp_phase = 'done'
        cfp_status = _('Closed')
    else:
        cfp_phase = 'pending'
        cfp_status = _('Pending')

    cfp_summary = ''
    if hasattr(event, 'cfp') and event.cfp.deadline:
        cfp_summary = str(event.cfp.deadline.strftime('%b %d, %Y'))

    # 2. Review
    if submitted_count > 0:
        review_phase = 'active'
        review_status = _('In progress')
    elif total_processed > 0:
        review_phase = 'done'
        review_status = _('Completed')
    else:
        review_phase = 'pending'
        review_status = _('Pending')

    review_summary = ''
    if rejected_count:
        review_summary = ngettext_lazy(
            '%(count)d rejected',
            '%(count)d rejected',
            rejected_count,
        ) % {'count': rejected_count}

    # 3. Acceptance
    if accepted_count > 0 or confirmed_count > 0:
        acceptance_phase = 'done'
        acceptance_status = _('Completed')
    else:
        acceptance_phase = 'pending'
        acceptance_status = _('Pending')

    acceptance_summary = ''
    if accepted_count:
        acceptance_summary = ngettext_lazy(
            '%(count)d accepted',
            '%(count)d accepted',
            accepted_count,
        ) % {'count': accepted_count}

    # 4. Confirmation
    if accepted_count > 0:
        confirmation_phase = 'active'
        confirmation_status = _('In progress')
    elif confirmed_count > 0:
        confirmation_phase = 'done'
        confirmation_status = _('Completed')
    else:
        confirmation_phase = 'pending'
        confirmation_status = _('Pending')

    confirmation_summary = ''
    if accepted_count:
        confirmation_summary = ngettext_lazy(
            '%(count)d unconfirmed',
            '%(count)d unconfirmed',
            accepted_count,
        ) % {'count': accepted_count}

    # 5. Scheduling
    if talk_count > 0 and unscheduled_count == 0:
        scheduling_phase = 'done'
        scheduling_status = _('Completed')
    elif unscheduled_count > 0 or talk_count > 0:
        scheduling_phase = 'active'
        scheduling_status = _('In progress')
    else:
        scheduling_phase = 'pending'
        scheduling_status = _('Pending')

    scheduling_summary = ''
    if unscheduled_count:
        scheduling_summary = ngettext_lazy(
            '%(count)d unscheduled',
            '%(count)d unscheduled',
            unscheduled_count,
        ) % {'count': unscheduled_count}

    # 6. Published
    if event.current_schedule:
        published_phase = 'done'
        published_status = _('Published')
        published_summary = str(event.current_schedule.version)
    else:
        published_phase = 'pending'
        published_status = _('Pending')
        published_summary = ''

    # 7. Live
    current_time = now()
    if event.date_to and current_time > event.date_to:
        live_phase = 'done'
        live_status = _('Ended')
    elif event.date_from and event.date_to and event.date_from <= current_time <= event.date_to:
        live_phase = 'active'
        live_status = _('Live')
    else:
        live_phase = 'pending'
        live_status = _('Pending')

    return [
        {
            'label': _('Call for proposals'),
            'status': cfp_status,
            'summary': cfp_summary,
            'phase': cfp_phase,
            'icon': 'bullhorn',
            'url': event.cfp.urls.text if hasattr(event, 'cfp') else '',
        },
        {
            'label': _('Review'),
            'status': review_status,
            'summary': review_summary,
            'phase': review_phase,
            'icon': 'eye',
            'url': event.orga_urls.reviews,
        },
        {
            'label': _('Acceptance'),
            'status': acceptance_status,
            'summary': acceptance_summary,
            'phase': acceptance_phase,
            'icon': 'check',
            'url': event.orga_urls.submissions,
        },
        {
            'label': _('Confirmation'),
            'status': confirmation_status,
            'summary': confirmation_summary,
            'phase': confirmation_phase,
            'icon': 'thumbs-up',
            'url': event.orga_urls.speakers,
        },
        {
            'label': _('Scheduling'),
            'status': scheduling_status,
            'summary': scheduling_summary,
            'phase': scheduling_phase,
            'icon': 'calendar-o',
            'url': event.orga_urls.schedule,
        },
        {
            'label': _('Published'),
            'status': published_status,
            'summary': published_summary,
            'phase': published_phase,
            'icon': 'globe',
            'url': event.urls.schedule,
        },
        {
            'label': _('Live'),
            'status': live_status,
            'summary': '',
            'phase': live_phase,
            'icon': 'play',
            'url': event.urls.schedule,
        },
    ]