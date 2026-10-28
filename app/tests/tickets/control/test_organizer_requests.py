import re
import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from eventyay.base.forms.organizer_request import OrganizerRequestForm
from eventyay.base.models import Organizer, OrganizerRequest, User
from eventyay.base.models.auth import StaffSession
from eventyay.base.services.organizer_requests import review_request


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def disable_video_cache_updates():
    with patch('eventyay.base.models.cache.VersionedModel._set_cache_version_sync'):
        yield


@pytest.fixture
def data():
    return {
        'name': 'Jane Example',
        'email': 'Jane@example.com',
        'affiliation': 'Example community',
        'events': 'A local meetup',
        'organizer_name': 'Example',
        'slug': 'example-community',
    }


@pytest.fixture
def application(data):
    return OrganizerRequest.objects.create(**{**data, 'email': data['email'].lower()})


@pytest.fixture
def admin(client):
    user = User.objects.create_user('admin@example.com', 'secret', is_staff=True)
    client.force_login(user)
    StaffSession.objects.create(user=user, session_key=client.session.session_key)
    return user


def test_public_form_and_submission(client, data, django_capture_on_commit_callbacks):
    User.objects.create_user('admin@example.com', is_staff=True)
    User.objects.create_user('super@example.com', is_superuser=True)
    assert client.get('/invite').status_code == 200
    with (
        patch('eventyay.base.services.organizer_requests.mail') as mail,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = client.post('/invite', data)
    assert response.status_code == 302
    assert response.url == reverse('organizer_request.success')
    assert 'within a few business days' in client.get(response.url).content.decode()
    assert OrganizerRequest.objects.get().email == 'jane@example.com'
    assert {call.args[0] for call in mail.call_args_list} == {
        'jane@example.com',
        'admin@example.com',
        'super@example.com',
    }
    assert not User.objects.filter(email='jane@example.com').exists()


def test_same_form_when_logged_in(client, admin):
    assert client.get('/invite').status_code == 200


@pytest.mark.parametrize('slug', ['UPPER', 'two words', 'control', 'invite', '-bad', 'bad/', 'a' * 51])
def test_invalid_slugs(client, data, slug):
    assert not OrganizerRequestForm(data={**data, 'slug': slug}).is_valid()
    assert client.get('/invite/slug/', {'slug': slug}).json()['available'] is False


def test_taken_slug(client, data):
    Organizer.objects.create(name='Existing', slug=data['slug'].upper())
    assert not OrganizerRequestForm(data=data).is_valid()
    assert not client.get('/invite/slug/', {'slug': data['slug']}).json()['available']
    assert client.get('/invite/slug/', {'slug': 'available'}).json()['available']


def test_duplicate_pending_email(application, data):
    assert 'email' in OrganizerRequestForm(data=data).errors
    with pytest.raises(IntegrityError), transaction.atomic():
        OrganizerRequest.objects.create(**data)
    application.status = 'rejected'
    application.save()
    assert OrganizerRequestForm(data=data).is_valid()


def test_honeypot(data):
    assert not OrganizerRequestForm(data={**data, 'website': 'spam'}).is_valid()


def test_rate_limit(client, settings):
    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    cache.clear()
    for _ in range(10):
        assert client.post('/invite', {}).status_code == 200
    assert client.post('/invite', {}).status_code == 429
    cache.clear()


def test_approve_new_account(application, admin, django_capture_on_commit_callbacks):
    with (
        patch('eventyay.base.services.organizer_requests.mail') as mail,
        django_capture_on_commit_callbacks(execute=True),
    ):
        result = review_request(application.pk, admin, approve=True, organizer_name='Edited name', slug='edited')
    assert result.status == 'approved'
    assert result.reviewed_by == admin and result.reviewed_at
    assert result.organizer.name == 'Edited name'
    assert result.new_account
    assert result.user.fullname == application.name
    assert not result.user.has_usable_password()
    team = result.user.teams.get(organizer=result.organizer)
    assert team.name == 'Core Organizing Team'
    assert team.can_create_events and team.all_events and team.can_change_teams
    assert 'Set your password:' in mail.call_args.args[3]['body']
    with pytest.raises(ValidationError):
        review_request(application.pk, admin, approve=True, organizer_name='Again', slug='again')
    assert not Organizer.objects.filter(slug='again').exists()


def test_existing_account(application, admin, mailoutbox, django_capture_on_commit_callbacks):
    user = User.objects.create_user(application.email, 'existing-password')
    with django_capture_on_commit_callbacks(execute=True):
        result = review_request(application.pk, admin, approve=True, organizer_name='Example', slug='example')
    assert len(mailoutbox) == 1
    assert 'sign in with your existing Eventyay account' in mailoutbox[0].body
    assert 'You do not need to create a new account or set a new password.' in mailoutbox[0].body
    assert result.user == user and not result.new_account
    user.refresh_from_db()
    assert user.check_password('existing-password')
    assert user.teams.filter(organizer=result.organizer, can_create_events=True).exists()


def test_reject(application, admin, django_capture_on_commit_callbacks):
    with (
        patch('eventyay.base.services.organizer_requests.mail') as mail,
        django_capture_on_commit_callbacks(execute=True),
    ):
        result = review_request(application.pk, admin, approve=False, reason='Please tell us more')
    assert result.status == 'rejected' and result.reviewed_by == admin
    assert not User.objects.filter(email=application.email).exists()
    assert result.organizer is None
    assert 'Please tell us more' in mail.call_args.args[3]['body']


def test_admin_review_pages(client, application, admin):
    url = reverse('eventyay_admin:admin.organizer_requests.detail', args=[application.pk])
    assert client.get(reverse('eventyay_admin:admin.organizer_requests')).status_code == 200
    assert client.get(url).status_code == 200
    response = client.post(url, {'action': 'approve', 'organizer_name': 'Changed', 'slug': 'changed'})
    assert response.status_code == 302
    application.refresh_from_db()
    assert application.status == 'approved'
    assert client.get(url).status_code == 200


def test_non_admin_cannot_review(client, application):
    client.force_login(User.objects.create_user('other@example.com'))
    url = reverse('eventyay_admin:admin.organizer_requests.detail', args=[application.pk])
    assert client.get(url).status_code == 403
    assert client.post(url, {'action': 'reject'}).status_code == 403
    application.refresh_from_db()
    assert application.status == 'pending'


def test_password_setup_and_reuse(client, application, admin):
    result = review_request(application.pk, admin, approve=True, organizer_name='Example', slug='example')
    client.logout()
    token = default_token_generator.make_token(result.user)
    url = reverse('eventyay_common:auth.forgot.recover') + f'?id={result.user.pk}&token={token}'
    assert client.get(url).status_code == 200
    before_login = int(time.time())
    response = client.post(
        url, {'password': 'Correct-Horse-Battery-123!', 'password_repeat': 'Correct-Horse-Battery-123!'}
    )
    assert response.status_code == 302
    assert response.url == reverse('control:organizer', kwargs={'organizer': 'example'})
    assert str(client.session['_auth_user_id']) == str(result.user.pk)
    assert before_login <= client.session['eventyay_auth_login_time'] <= int(time.time())
    client.logout()
    assert client.get(url).url == reverse('eventyay_common:auth.forgot')


def test_expired_setup_link(client, application, admin, settings):
    result = review_request(application.pk, admin, approve=True, organizer_name='Example', slug='example')
    token = default_token_generator.make_token(result.user)
    client.logout()
    settings.PASSWORD_RESET_TIMEOUT = -1
    url = reverse('eventyay_common:auth.forgot.recover') + f'?id={result.user.pk}&token={token}'
    assert client.get(url).url == reverse('eventyay_common:auth.forgot')
    result.user.refresh_from_db()
    assert not result.user.has_usable_password()


def test_reject_with_taken_slug(client, application, admin):
    Organizer.objects.create(name='Taken', slug=application.slug)
    url = reverse('eventyay_admin:admin.organizer_requests.detail', args=[application.pk])
    assert client.post(url, {'action': 'reject', 'reason': ''}).status_code == 302
    application.refresh_from_db()
    assert application.status == 'rejected'


def test_slug_collision_rolls_back(application, admin):
    Organizer.objects.create(name='Taken', slug='taken')
    with pytest.raises(ValidationError):
        review_request(application.pk, admin, approve=True, organizer_name='Example', slug='taken')
    assert not User.objects.filter(email=application.email).exists()
    application.refresh_from_db()
    assert application.status == 'pending'


@pytest.mark.parametrize('flag', ['is_spam', 'is_active'])
def test_disabled_accounts_not_granted_access(application, admin, flag):
    User.objects.create_user(application.email, **{flag: flag == 'is_spam'})
    with pytest.raises(ValidationError):
        review_request(application.pk, admin, approve=True, organizer_name='Example', slug='example')
    assert not Organizer.objects.filter(slug='example').exists()


def test_events_length(data):
    assert 'events' in OrganizerRequestForm(data={**data, 'events': 'x' * 10001}).errors


def test_normal_password_reset_does_not_auto_login(client):
    user = User.objects.create_user('existing@example.com', 'old-password')
    token = default_token_generator.make_token(user)
    url = reverse('eventyay_common:auth.forgot.recover') + f'?id={user.pk}&token={token}'
    page = client.get(url).content.decode()
    assert 'Set new password' in page
    assert 'Set password and continue' not in page
    response = client.post(
        url, {'password': 'Correct-Horse-Battery-123!', 'password_repeat': 'Correct-Horse-Battery-123!'}
    )
    assert response.url == reverse('auth.login')
    assert '_auth_user_id' not in client.session


def test_forgot_password_replacement_link(client, application, admin, mailoutbox):
    result = review_request(application.pk, admin, approve=True, organizer_name='Example', slug='example')
    client.logout()
    response = client.post(reverse('eventyay_common:auth.forgot'), {'email': application.email})
    assert response.status_code == 302
    assert len(mailoutbox) == 1
    assert f'id={result.user.pk}' in mailoutbox[0].body
    assert 'token=' in mailoutbox[0].body


def test_submission_email_rendering(client, data, mailoutbox, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        assert client.post('/invite', data).status_code == 302
    assert len(mailoutbox) == 1
    assert 'within a few business days' in mailoutbox[0].body


def test_welcome_email_password_link(client, application, admin, mailoutbox, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        result = review_request(application.pk, admin, approve=True, organizer_name='Example', slug='example')
    assert len(mailoutbox) == 1
    body = mailoutbox[0].body
    assert 'Set password and continue' in body
    assert 'signed in automatically and taken to your organiser dashboard' in body
    assert application.email in body
    setup_url = re.search(r'https?://[^\s]+/forgot/recover/\?[^\s]+', body).group()
    query = parse_qs(urlsplit(setup_url).query)
    assert query['id'] == [str(result.user.pk)]
    assert default_token_generator.check_token(result.user, query['token'][0])
    assert '&amp;' not in setup_url
    client.logout()
    page = client.get(setup_url)
    assert page.status_code == 200
    assert 'Welcome to Eventyay' in page.content.decode()
    assert 'Set password and continue' in page.content.decode()
    assert 'Example' in page.content.decode()
    assert 'create your first event' in page.content.decode()
    response = client.post(
        setup_url,
        {'password': 'Correct-Horse-Battery-123!', 'password_repeat': 'Correct-Horse-Battery-123!'},
    )
    assert response.url == reverse('control:organizer', kwargs={'organizer': result.organizer.slug})
    assert str(client.session['_auth_user_id']) == str(result.user.pk)
