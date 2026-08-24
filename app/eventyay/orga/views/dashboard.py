from django.db.models import Count, Q
from django.shortcuts import redirect
from django.template.defaultfilters import timeuntil
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy
from django.views.generic import TemplateView
from django_context_decorator import context
from django_scopes import scopes_disabled
from django.contrib import messages

from django.http import Http404

def legacy_orga_event_redirect(request, event):
    from eventyay.base.models import Event
    with scopes_disabled():
        events = Event.objects.filter(slug__iexact=event)
        if events.count() == 1:
            e = events.first()
            url = f"/orga/event/{e.organizer.slug}/{e.slug}/"
            if request.META.get('QUERY_STRING'):
                url += '?' + request.META['QUERY_STRING']
            return redirect(url, permanent=True)
        if events.count() > 1 and request.user.is_authenticated:
            user_events = events.filter(
                Q(organizer__id__in=request.user.teams.values_list('organizer_id', flat=True)) |
                Q(submissions__speakers__in=[request.user])
            ).distinct()
            if user_events.count() == 1:
                e = user_events.first()
                url = f"/orga/event/{e.organizer.slug}/{e.slug}/"
                if request.META.get('QUERY_STRING'):
                    url += '?' + request.META['QUERY_STRING']
                return redirect(url, permanent=True)
        raise Http404()

from eventyay.base.models import Submission, SubmissionStates
from eventyay.base.models.event import Event
from eventyay.base.models.log import LogEntry
from eventyay.base.models.organizer import Organizer
from eventyay.base.models.profile import SpeakerProfile
from eventyay.base.settings import is_event_series_creation_enabled, is_meetup_creation_enabled
from eventyay.common.text.phrases import phrases
from eventyay.common.permissions import is_admin_mode_active
from eventyay.common.views.mixins import EventPermissionRequired, PermissionRequired
from eventyay.event.stages import get_stages
from eventyay.orga.views.submission import SubmissionStatsMixin
from eventyay.talk_rules.submission import get_missing_reviews


def start_redirect_view(request):
    with scopes_disabled():
        orga_events = set(request.user.get_events_with_any_permission())
        speaker_events = set(Event.objects.filter(submissions__speakers__in=[request.user]))

    # Users with only one event, in only one role, are redirected to that event
    if len(orga_events | speaker_events) == 1 and not (orga_events and speaker_events):
        if orga_events:
            return redirect(orga_events.pop().orga_urls.base)
        return redirect(speaker_events.pop().urls.user_submissions)

    return redirect(reverse('eventyay_common:dashboard'))


class DashboardEventListView(TemplateView):
    template_name = 'orga/event_list.html'

    @property
    def base_queryset(self):
        return self.request.user.get_events_with_any_permission()

    @cached_property
    def queryset(self):
        if is_admin_mode_active(self.request):
            qs = Event.objects.all()
        else:
            qs = self.base_queryset.annotate(
                submission_count=Count(
                    'submissions',
                    filter=Q(
                        submissions__state__in=[
                            state
                            for state in SubmissionStates.display_values.keys()
                            if state not in (SubmissionStates.DELETED, SubmissionStates.DRAFT)
                        ]
                    ),
                )
            ).order_by('-date_from')
        if search := self.request.GET.get('q'):
            qs = qs.filter(Q(name__icontains=search) | Q(slug__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_orga_events'] = []
        context['past_orga_events'] = []
        for event in self.queryset:
            if event.date_to >= now():
                context['current_orga_events'].insert(0, event)
            else:
                context['past_orga_events'].append(event)
        context['speaker_events'] = (
            Event.objects.filter(submissions__speakers__in=[self.request.user]).distinct().order_by('-date_from')
        )
        context['event_series_creation_enabled'] = is_event_series_creation_enabled(self.request)
        context['meetup_creation_enabled'] = is_meetup_creation_enabled(self.request)
        return context


class DashboardOrganizerEventListView(PermissionRequired, DashboardEventListView):
    permission_required = 'base.view_organizer'

    def get_permission_object(self):
        return self.request.organizer

    @property
    def base_queryset(self):
        return self.request.organizer.events.all()

    @context
    def hide_speaker_events(self):
        return True


class DashboardOrganizerListView(PermissionRequired, TemplateView):
    template_name = 'orga/organizer/list.html'
    permission_required = 'base.list_organizer'

    def filter_organizer(self, organizer, query):
        name = {'en': organizer.name} if isinstance(organizer.name, str) else organizer.name.data
        name = {'en': name} if isinstance(name, str) else name
        return query in organizer.slug or any(query in value for value in name.values())

    @context
    def organizers(self):
        if self.request.user.is_administrator:
            orgs = Organizer.objects.all()
        else:
            orgs = Organizer.objects.filter(
                pk__in={
                    team.organizer_id for team in self.request.user.teams.filter(can_change_organizer_settings=True)
                }
            )
        orgs = orgs.annotate(
            event_count=Count('events', distinct=True),
            team_count=Count('teams', distinct=True),
        )
        query = self.request.GET.get('q')
        if not query:
            return orgs
        query = query.lower().strip()
        return [org for org in orgs if self.filter_organizer(org, query)]


class EventDashboardView(EventPermissionRequired, SubmissionStatsMixin, TemplateView):
    template_name = 'orga/event/dashboard.html'
    permission_required = 'base.talk_orga_access_event'

    def get_cfp_tiles(self, _now, can_change_submissions=False):
        result = []
        if not hasattr(self.request.event, 'cfp'):
            return result
        if self.request.event.cfp.is_open:
            result.append(
                {
                    'url': self.request.event.cfp.urls.public,
                    'large': phrases.cfp.go_to_cfp,
                    'priority': 20,
                }
            )
        max_deadline = self.request.event.cfp.max_deadline
        if max_deadline and _now < max_deadline:
            result.append(
                {
                    'large': timeuntil(max_deadline),
                    'small': _('until the CfP ends'),
                    'priority': 40,
                }
            )
            draft_proposals = Submission.all_objects.filter(
                state=SubmissionStates.DRAFT, event=self.request.event
            ).count()
            if draft_proposals and can_change_submissions:
                result.append(
                    {
                        'large': draft_proposals,
                        'small': ngettext_lazy(
                            'unsubmitted proposal draft',
                            'unsubmitted proposal drafts',
                            draft_proposals,
                        ),
                        'priority': 50,
                        'url': self.request.event.orga_urls.send_drafts_reminder,
                        'left': {
                            'text': _('Send reminder'),
                            'url': self.request.event.orga_urls.send_drafts_reminder,
                            'color': 'info',
                        },
                    }
                )
        return result

    def get_review_tiles(self, can_change_settings):
        result = []
        review_count = self.request.event.reviews.count()
        if review_count:
            active_reviewers = (
                self.request.event.reviewers.filter(reviews__isnull=False).order_by('id').distinct().count()
            )
            result.append({'large': review_count, 'small': _('Reviews'), 'priority': 60})
            result.append(
                {
                    'large': active_reviewers,
                    'small': _('Active reviewers'),
                    'url': (self.request.event.organizer.orga_urls.teams if can_change_settings else None),
                    'priority': 60,
                }
            )
        is_reviewer = self.request.event.teams.filter(members__in=[self.request.user], is_reviewer=True).exists()
        if is_reviewer:
            reviews_missing = get_missing_reviews(self.request.event, self.request.user).count()
            if reviews_missing:
                result.append(
                    {
                        'large': reviews_missing,
                        'small': ngettext_lazy(
                            'proposal is waiting for your review.',
                            'proposals are waiting for your review.',
                            reviews_missing,
                        ),
                        'url': self.request.event.orga_urls.reviews,
                        'priority': 21,
                    }
                )
        return result

    @context
    def history(self):
        return LogEntry.objects.filter(event=self.request.event).select_related('user', 'event')[:20]

    # ------------------------------------------------------------------
    # New helper methods for the redesigned dashboard sections
    # ------------------------------------------------------------------

    def _get_submission_counts(self, event):
        """Return a dict of submission counts by state."""
        from django.db.models import Count as DbCount
        counts = {
            'submitted': event.submissions.filter(state=SubmissionStates.SUBMITTED).count(),
            'accepted': event.submissions.filter(state=SubmissionStates.ACCEPTED).count(),
            'confirmed': event.submissions.filter(state=SubmissionStates.CONFIRMED).count(),
            'rejected': Submission.all_objects.filter(
                event=event, state=SubmissionStates.REJECTED
            ).count(),
            'withdrawn': Submission.all_objects.filter(
                event=event, state=SubmissionStates.WITHDRAWN
            ).count(),
            'drafts': event.submissions.filter(
                state=SubmissionStates.DRAFT
            ).count(),
            'total': Submission.all_objects.exclude(
                state__in=[SubmissionStates.DELETED, SubmissionStates.DRAFT]
            ).filter(event=event).count(),
        }
        return counts

    def _build_workflow_steps(self, event, stages, sub_counts):
        """Build a list of workflow step dicts for the labeled timeline."""
        cfp = getattr(event, 'cfp', None)

        cfp_status = _('Open') if (cfp and cfp.is_open) else _('Closed')
        cfp_detail = ''
        if cfp and cfp.deadline:
            cfp_detail = str(cfp.deadline.strftime('%b %-d'))

        steps = [
            {
                'label': _('Call for proposals'),
                'status': cfp_status,
                'detail': cfp_detail,
                'phase': 'done' if not (cfp and cfp.is_open) else 'current',
                'icon': 'bullhorn',
            },
            {
                'label': _('Review'),
                'status': _('Completed') if stages['REVIEW']['phase'] == 'done' else (
                    _('In progress') if stages['REVIEW']['phase'] == 'current' else _('Pending')
                ),
                'detail': str(sub_counts['rejected']) + ' ' + str(_('rejected')) if sub_counts['rejected'] else '',
                'phase': stages['REVIEW']['phase'],
                'icon': 'eye',
            },
            {
                'label': _('Acceptance'),
                'status': _('Completed') if sub_counts['accepted'] + sub_counts['confirmed'] > 0 and sub_counts['submitted'] == 0 else (
                    _('In progress') if sub_counts['accepted'] > 0 else _('Pending')
                ),
                'detail': str(sub_counts['accepted'] + sub_counts['confirmed']) + ' ' + str(_('accepted')),
                'phase': 'done' if (sub_counts['accepted'] + sub_counts['confirmed'] > 0 and sub_counts['submitted'] == 0)
                         else ('current' if sub_counts['accepted'] > 0 else 'pending'),
                'icon': 'check-circle',
            },
            {
                'label': _('Confirmation'),
                'status': _('In progress') if sub_counts['accepted'] > 0 else (
                    _('Completed') if sub_counts['confirmed'] > 0 else _('Pending')
                ),
                'detail': str(sub_counts['accepted']) + ' ' + str(_('unconfirmed')) if sub_counts['accepted'] else '',
                'phase': 'issue' if sub_counts['accepted'] > 0 else (
                    'done' if sub_counts['confirmed'] > 0 else 'pending'
                ),
                'icon': 'user-check',
            },
            {
                'label': _('Scheduling'),
                'status': _('Completed') if stages['SCHEDULE']['phase'] == 'done' else (
                    _('In progress') if stages['SCHEDULE']['phase'] == 'current' else _('Pending')
                ),
                'detail': '',
                'phase': stages['SCHEDULE']['phase'],
                'icon': 'calendar',
            },
            {
                'label': _('Published'),
                'status': _('Live') if event.talks_published else _('Pending'),
                'detail': '',
                'phase': 'done' if event.talks_published else 'pending',
                'icon': 'globe',
            },
            {
                'label': _('Live'),
                'status': _('Running') if stages['EVENT']['phase'] == 'current' else (
                    _('Done') if stages['EVENT']['phase'] == 'done' else _('Pending')
                ),
                'detail': '',
                'phase': stages['EVENT']['phase'],
                'icon': 'play-circle',
            },
        ]
        return steps

    def _build_action_items(self, event, sub_counts, can_change_submissions):
        """Return all action item types, always. Use 'active' flag to distinguish
        items that need attention vs those that are fine."""
        items = []

        unconfirmed = sub_counts['accepted']
        items.append({
            'title': _('Unconfirmed sessions'),
            'desc': ngettext_lazy(
                '{n} accepted session is waiting for speaker confirmation.',
                '{n} accepted sessions are waiting for speaker confirmation.',
                max(unconfirmed, 1),
            ).format(n=unconfirmed) if unconfirmed else _('All accepted sessions have been confirmed.'),
            'count': unconfirmed,
            'url': event.orga_urls.submissions + f'?state={SubmissionStates.ACCEPTED}',
            'btn': _('Review sessions'),
            'color': 'warning',
            'icon': 'exclamation-triangle',
            'active': bool(unconfirmed and can_change_submissions),
        })

        # Pending reviews
        pending_reviews = get_missing_reviews(event, self.request.user).count()
        items.append({
            'title': _('Pending reviews'),
            'desc': ngettext_lazy(
                '{n} proposal is waiting for your review.',
                '{n} proposals are waiting for your review.',
                max(pending_reviews, 1),
            ).format(n=pending_reviews) if pending_reviews else _('No proposals waiting for review.'),
            'count': pending_reviews,
            'url': event.orga_urls.reviews,
            'btn': _('Go to reviews'),
            'color': 'info',
            'icon': 'eye',
            'active': bool(pending_reviews),
        })

        # Speakers with incomplete profiles (missing biography)
        speakers_missing_bio = SpeakerProfile.objects.filter(
            event=event,
            user__submissions__event=event,
            user__submissions__state__in=SubmissionStates.accepted_states,
        ).filter(
            Q(biography__isnull=True) | Q(biography='')
        ).distinct().count()
        items.append({
            'title': _('Speakers incomplete'),
            'desc': ngettext_lazy(
                '{n} speaker is missing a biography.',
                '{n} speakers are missing a biography.',
                max(speakers_missing_bio, 1),
            ).format(n=speakers_missing_bio) if speakers_missing_bio else _('All speaker profiles are complete.'),
            'count': speakers_missing_bio,
            'url': event.orga_urls.speakers + '?role=true',
            'btn': _('Review speakers'),
            'color': 'warning',
            'icon': 'user-times',
            'active': bool(speakers_missing_bio and can_change_submissions),
        })

        # Pending outbox notifications
        pending_notifications = event.queued_mails.filter(sent__isnull=True).count()
        items.append({
            'title': _('Notifications pending'),
            'desc': ngettext_lazy(
                '{n} email is waiting to be sent.',
                '{n} emails are waiting to be sent.',
                max(pending_notifications, 1),
            ).format(n=pending_notifications) if pending_notifications else _('No pending email notifications.'),
            'count': pending_notifications,
            'url': event.orga_urls.outbox,
            'btn': _('Send notifications'),
            'color': 'primary',
            'icon': 'envelope',
            'active': bool(pending_notifications),
        })

        return sorted(items, key=lambda x: (0 if x['active'] else 1))

    def _build_kpi_cards(self, event, sub_counts):
        """Return KPI card data for the At a Glance section."""
        total = sub_counts['total']
        accepted = sub_counts['accepted']
        confirmed = sub_counts['confirmed']
        submitted = sub_counts['submitted']
        rejected = sub_counts['rejected']
        withdrawn = sub_counts['withdrawn']
        drafts = sub_counts.get('drafts', 0)
        speaker_count = event.speakers.count()
        pending_reviews = event.submissions.filter(state=SubmissionStates.SUBMITTED).count()
        emails_sent = event.queued_mails.filter(sent__isnull=False).count()
        talk_count = event.talks.count()

        current_schedule = getattr(event, 'current_schedule', None)
        schedule_version = current_schedule.version if current_schedule else '-'

        from eventyay.base.models.review import Review
        active_reviewers = Review.objects.filter(submission__event=event).values('user').distinct().count()

        cards = [
            {
                'label': _('Submitted proposals'),
                'value': total,
                'url': event.orga_urls.submissions,
                'link': _('View all'),
                'color': '',
                'icon': 'inbox',
            },
            {
                'label': _('Accepted proposals'),
                'value': accepted + confirmed,
                'url': event.orga_urls.submissions + f'?state={SubmissionStates.ACCEPTED}&state={SubmissionStates.CONFIRMED}',
                'link': _('View all'),
                'color': 'success',
                'icon': 'check',
            },
            {
                'label': _('Confirmed sessions'),
                'value': confirmed,
                'url': event.orga_urls.submissions + f'?state={SubmissionStates.CONFIRMED}',
                'link': _('View all'),
                'color': 'success',
                'icon': 'check-circle',
            },
            {
                'label': _('Scheduled sessions'),
                'value': talk_count,
                'url': event.orga_urls.schedule,
                'link': _('View schedule'),
                'color': 'success' if talk_count else '',
                'icon': 'calendar',
            },
            {
                'label': _('Speakers'),
                'value': speaker_count,
                'url': event.orga_urls.speakers + '?role=true',
                'link': _('View speakers'),
                'color': '',
                'icon': 'users',
            },
            {
                'label': _('Pending reviews'),
                'value': submitted,
                'url': event.orga_urls.reviews,
                'link': _('Review now'),
                'color': 'warning' if submitted else 'muted',
                'icon': 'eye',
            },
            {
                'label': _('Rejected proposals'),
                'value': rejected,
                'url': event.orga_urls.submissions + f'?state={SubmissionStates.REJECTED}',
                'link': _('View all'),
                'color': 'danger' if rejected else 'muted',
                'icon': 'times',
            },
            {
                'label': _('Withdrawn proposals'),
                'value': withdrawn,
                'url': event.orga_urls.submissions + f'?state={SubmissionStates.WITHDRAWN}',
                'link': _('View all'),
                'color': 'muted',
                'icon': 'undo',
            },
            {
                'label': _('Emails sent'),
                'value': emails_sent,
                'url': event.orga_urls.sent_mails,
                'link': _('View history'),
                'color': '',
                'icon': 'envelope',
            },
            {
                'label': _('Current schedule'),
                'value': schedule_version,
                'url': event.orga_urls.schedule,
                'link': _('View schedule'),
                'color': '',
                'icon': 'calendar-check-o',
            },
            {
                'label': _('Active reviewers'),
                'value': active_reviewers,
                'url': event.orga_urls.reviews,
                'link': _('View reviews'),
                'color': '',
                'icon': 'user-circle',
            },
            {
                'label': _('Unsubmitted proposal draft'),
                'value': drafts,
                'url': event.orga_urls.submissions + f'?state={SubmissionStates.DRAFT}',
                'link': _('View drafts'),
                'color': '',
                'icon': 'pencil',
            },
        ]
        return cards

    def _build_funnel_data(self, sub_counts):
        """Return funnel bar data with normalised widths for the submission funnel."""
        total = sub_counts['total'] or 1  # avoid division by zero
        rows = [
            {'label': _('Submitted'), 'count': sub_counts['total'], 'key': 'submitted', 'pct': 100},
            {'label': _('Accepted'), 'count': sub_counts['accepted'] + sub_counts['confirmed'], 'key': 'accepted',
             'pct': round((sub_counts['accepted'] + sub_counts['confirmed']) / total * 100)},
            {'label': _('Confirmed'), 'count': sub_counts['confirmed'], 'key': 'confirmed',
             'pct': round(sub_counts['confirmed'] / total * 100)},
            {'label': _('Rejected'), 'count': sub_counts['rejected'], 'key': 'rejected',
             'pct': round(sub_counts['rejected'] / total * 100)},
            {'label': _('Withdrawn'), 'count': sub_counts['withdrawn'], 'key': 'withdrawn',
             'pct': round(sub_counts['withdrawn'] / total * 100)},
        ]
        accepted_total = sub_counts['accepted'] + sub_counts['confirmed']
        conversion = round(accepted_total / total * 100) if total > 1 else 0
        return {'rows': rows, 'conversion': conversion}

    def _build_session_readiness(self, event):
        """Return session readiness data."""
        confirmed = event.submissions.filter(state=SubmissionStates.CONFIRMED).count()
        unconfirmed = event.submissions.filter(state=SubmissionStates.ACCEPTED).count()
        scheduled = event.talks.count()
        unscheduled = max(0, confirmed - scheduled)
        return {
            'total': confirmed + unconfirmed,
            'confirmed': confirmed,
            'unconfirmed': unconfirmed,
            'scheduled': scheduled,
            'unscheduled': unscheduled,
            'sessions_url': event.orga_urls.submissions + f'?state={SubmissionStates.CONFIRMED}',
            'unconfirmed_url': event.orga_urls.submissions + f'?state={SubmissionStates.ACCEPTED}',
            'schedule_url': event.orga_urls.schedule,
        }

    def _build_speaker_readiness(self, event):
        """Return speaker readiness data."""
        total_speakers = event.speakers.count()
        # Confirmed speakers = speakers with at least one confirmed submission
        confirmed_speakers = event.speakers.filter(
            submissions__state=SubmissionStates.CONFIRMED,
            submissions__event=event,
        ).distinct().count()
        missing_bio = SpeakerProfile.objects.filter(
            event=event,
        ).filter(
            Q(biography__isnull=True) | Q(biography='')
        ).count()
        missing_avatar = SpeakerProfile.objects.filter(
            event=event,
            user__avatar='',
        ).count()
        return {
            'total': total_speakers,
            'confirmed': confirmed_speakers,
            'missing_bio': missing_bio,
            'missing_avatar': missing_avatar,
            'speakers_url': event.orga_urls.speakers + '?role=true',
        }

    def _build_recent_activity(self, event):
        """Return the 10 most recent talk-related log entries."""
        talk_action_prefixes = (
            'eventyay.submission.',
            'eventyay.speaker.',
            'eventyay.schedule.',
            'eventyay.mail.',
            'eventyay.cfp.',
            'eventyay.review.',
        )
        q = Q()
        for prefix in talk_action_prefixes:
            q |= Q(action_type__startswith=prefix)
        return (
            LogEntry.objects.filter(event=event)
            .filter(q)
            .select_related('user', 'event', 'content_type')
            .order_by('-datetime')[:10]
        )

    def get_context_data(self, **kwargs):
        # Tiles can have priorities
        # Priorities are meant to be between 0 and 100
        # 0 is the first tile, the go-live tile
        # 100+ is whatever can go to the very end
        # actions should be between 10 and 30, with 20 being the "go to cfp" action
        # general stats start at 50
        result = super().get_context_data(**kwargs)
        event = self.request.event
        stages = get_stages(event)
        result['timeline'] = stages.values()
        result['go_to_target'] = 'schedule' if stages['REVIEW']['phase'] == 'done' else 'cfp'
        _now = now()
        today = _now
        can_change_settings = self.request.user.has_perm('base.change_settings.event', event)
        can_change_submissions = self.request.user.has_perm('base.orga_update_submission', event)
        result['tiles'] = self.get_cfp_tiles(_now, can_change_submissions=can_change_submissions)
        if today < event.date_from:
            days = (event.date_from - today).days
            result['tiles'].append(
                {
                    'large': days,
                    'small': ngettext_lazy('day until event start', 'days until event start', days),
                    'priority': 10,
                }
            )
        elif today > event.date_to:
            days = (today - event.date_from).days
            result['tiles'].append(
                {
                    'large': days,
                    'small': ngettext_lazy('day since event end', 'days since event end', days),
                    'priority': 80,
                }
            )
        elif event.date_to != event.date_from:
            day = (today - event.date_from).days + 1
            result['tiles'].append(
                {
                    'large': _('Day {number}').format(number=day),
                    'small': _('of {total_days} days').format(total_days=(event.date_to - event.date_from).days + 1),
                    'url': event.urls.schedule + f'#{today.isoformat()}',
                    'priority': 10,
                }
            )
        if event.current_schedule:
            result['tiles'].append(
                {
                    'large': event.current_schedule.version,
                    'small': _('current schedule'),
                    'url': event.urls.schedule,
                    'priority': 25,
                }
            )

        talk_count = event.talks.count()
        accepted_count = event.submissions.filter(state=SubmissionStates.ACCEPTED).count()
        submission_count = event.submissions.count()
        pending_state_submissions = event.submissions.filter(pending_state__isnull=False).count()
        if talk_count or accepted_count:
            confirmed_count = event.submissions.filter(state=SubmissionStates.CONFIRMED).count()
            result['tiles'].append(
                {
                    # Don't show 0 here for events that do not use the scheduling
                    # component, instead show accepted + confirmed
                    'large': talk_count or (accepted_count + confirmed_count),
                    'small': ngettext_lazy('session', 'sessions', talk_count),
                    'url': event.orga_urls.submissions
                    + f'?state={SubmissionStates.ACCEPTED}&state={SubmissionStates.CONFIRMED}',
                    'priority': 55,
                    'right': {
                        'text': str(_('unconfirmed')) + f': {accepted_count}',
                        'url': event.orga_urls.submissions + f'?state={SubmissionStates.ACCEPTED}',
                        'color': 'error' if accepted_count else 'info',
                    },
                    'left': {
                        'text': str(_('confirmed')) + f': {confirmed_count}',
                        'url': event.orga_urls.submissions,
                        'color': 'success',
                    },
                }
            )
        elif submission_count:
            count = event.submissions.count()
            result['tiles'].append(
                {
                    'large': count,
                    'small': ngettext_lazy('proposal', 'proposals', count),
                    'url': event.orga_urls.submissions,
                    'priority': 60,
                }
            )
        if pending_state_submissions and pending_state_submissions > 0:
            states = '&'.join(
                [
                    f'state=pending_state__{state}'
                    for state, __ in SubmissionStates.get_choices()
                    if state not in (SubmissionStates.DRAFT, SubmissionStates.DELETED)
                ]
            )
            result['tiles'].append(
                {
                    'large': pending_state_submissions,
                    'small': ngettext_lazy(
                        'submission with pending changes',
                        'submissions with pending changes',
                        pending_state_submissions,
                    ),
                    'url': event.orga_urls.submissions + f'?{states}',
                    'priority': 56,
                }
            )
        submitter_count = event.submitters.count()
        speaker_count = event.speakers.count()
        rejected_count = event.submitters.filter(submissions__state=SubmissionStates.REJECTED).distinct().count()
        if speaker_count:
            result['tiles'].append(
                {
                    'large': speaker_count,
                    'small': ngettext_lazy('speaker', 'speakers', speaker_count),
                    'url': event.orga_urls.speakers + '?role=true',
                    'priority': 56,
                    'right': {
                        'text': _('rejected') + f': {rejected_count}',
                        'url': event.orga_urls.speakers + '?role=false',
                        'color': 'error',
                    },
                    'left': {
                        'text': phrases.submission.submitted + f': {submitter_count}',
                        'url': event.orga_urls.speakers,
                        'color': 'success',
                    },
                }
            )
        else:
            result['tiles'].append(
                {
                    'large': submitter_count,
                    'small': ngettext_lazy('submitter', 'submitters', submitter_count),
                    'url': event.orga_urls.speakers,
                    'priority': 60,
                }
            )
        count = event.queued_mails.filter(sent__isnull=False).count()
        result['tiles'].append(
            {
                'large': count,
                'small': ngettext_lazy('sent email', 'sent emails', count),
                'url': event.orga_urls.sent_mails,
                'priority': 80,
            }
        )
        result['tiles'] += self.get_review_tiles(can_change_settings=can_change_settings)
        result['tiles'].sort(key=lambda tile: tile.get('priority') or 100)

        # ------------------------------------------------------------------
        # New dashboard context: workflow, actions, KPIs, funnel, readiness
        # ------------------------------------------------------------------
        sub_counts = self._get_submission_counts(event)
        result['workflow_steps'] = self._build_workflow_steps(event, stages, sub_counts)
        result['action_items'] = self._build_action_items(event, sub_counts, can_change_submissions)
        result['kpi_cards'] = self._build_kpi_cards(event, sub_counts)
        result['funnel_data'] = self._build_funnel_data(sub_counts)
        result['session_readiness'] = self._build_session_readiness(event)
        result['speaker_readiness'] = self._build_speaker_readiness(event)
        result['recent_activity'] = self._build_recent_activity(event)
        result['can_change_settings'] = can_change_settings
        result['can_change_submissions'] = can_change_submissions
        result['event_comment'] = getattr(event, 'comment', '') or ''

        return result

    def post(self, request, *args, **kwargs):
        """Handle internal note save from the talks dashboard."""
        if not request.user.has_perm('base.change_settings.event', request.event):
            messages.error(request, _('You do not have permission to change event settings.'))
        elif 'internal_note' in request.POST:
            note = request.POST.get('internal_note', '')
            request.event.comment = note
            request.event.save(update_fields=['comment'])
            request.event.log_action('eventyay.event.comment', person=request.user, orga=True)
            messages.success(request, _('Internal note saved.'))
        return redirect(request.event.orga_urls.base)
