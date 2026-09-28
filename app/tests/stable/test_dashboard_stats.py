import pytest
from django.urls import reverse
from django.utils.timezone import now
from eventyay.base.models import Event, Organizer, Submission, User
from eventyay.base.models.submission import SpeakerRole
from django_scopes import scopes_disabled

@pytest.fixture
def test_user():
    return User.objects.create_user('stats@example.com', 'password')

@pytest.fixture
def staff_user():
    user = User.objects.create_user('staff@example.com', 'password')
    user.is_staff = True
    user.is_active = True
    user.save()
    return user

@pytest.fixture
def orga(test_user):
    organizer = Organizer.objects.create(name='Stats Orga', slug='stats-orga')
    team = organizer.teams.create(
        name='Admins',
        can_change_organizer_settings=True,
        can_create_events=True,
    )
    team.members.add(test_user)
    return organizer

@pytest.fixture
def events_with_stats(orga, test_user):
    with scopes_disabled():
        e1 = Event.objects.create(organizer=orga, name='Event 1', slug='e1', date_from=now())
        e2 = Event.objects.create(organizer=orga, name='Event 2', slug='e2', date_from=now())

        # Event 1: 1 confirmed session, 1 draft session
        s1 = Submission.objects.create(event=e1, title='S1', state=Submission.STATE_CONFIRMED)
        s2 = Submission.objects.create(event=e1, title='S2', state=Submission.STATE_DRAFT)

        # Event 1: speakers
        # Speaker 1 on confirmed session
        SpeakerRole.objects.create(event=e1, submission=s1, user=test_user)
        # Speaker 2 on draft session (should be excluded)
        u2 = User.objects.create_user('s2@example.com', 'password')
        SpeakerRole.objects.create(event=e1, submission=s2, user=u2)
        # Speaker 1 also on draft session (should still be counted once)
        SpeakerRole.objects.create(event=e1, submission=s2, user=test_user)

        # Event 2: 0 sessions, 0 speakers

        return e1, e2

@pytest.mark.django_db
class TestEventListStats:
    def test_orga_event_list_stats(self, client, test_user, events_with_stats):
        client.force_login(test_user)
        response = client.get('/orga/event/')
        assert response.status_code == 200

        # Check the context for the injected stats
        events = response.context['events']
        events_dict = {e.slug: e for e in events}

        e1 = events_dict['e1']
        assert hasattr(e1, 'session_counts')
        assert hasattr(e1, 'speaker_counts')

        # Check session counts
        assert e1.session_counts[Submission.STATE_CONFIRMED] == 1
        assert e1.session_counts[Submission.STATE_DRAFT] == 0  # Not counted or zero based on implementation

        # Check speaker counts
        assert e1.speaker_counts[Submission.STATE_CONFIRMED] == 1
        assert e1.speaker_counts['total'] == 1

        e2 = events_dict['e2']
        assert e2.session_counts.get(Submission.STATE_CONFIRMED, 0) == 0
        assert e2.speaker_counts.get('total', 0) == 0

    def test_admin_event_list_stats(self, staff_client, events_with_stats):
        response = staff_client.get('/admin/events/')
        assert response.status_code == 200

        events = response.context['events']
        events_dict = {e.slug: e for e in events}

        e1 = events_dict['e1']
        assert hasattr(e1, 'session_counts')
        assert hasattr(e1, 'speaker_counts')

        assert e1.session_counts[Submission.STATE_CONFIRMED] == 1
        assert e1.speaker_counts[Submission.STATE_CONFIRMED] == 1
        assert e1.speaker_counts['total'] == 1

        e2 = events_dict['e2']
        assert e2.session_counts.get(Submission.STATE_CONFIRMED, 0) == 0
        assert e2.speaker_counts.get('total', 0) == 0
