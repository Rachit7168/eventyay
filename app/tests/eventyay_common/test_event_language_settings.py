from datetime import timedelta

import pytest
from django import forms
from django.utils import timezone
from django_scopes import scopes_disabled

from eventyay.base.models import Event
from eventyay.eventyay_common.forms.event import EventCommonSettingsForm


@pytest.mark.django_db
@scopes_disabled()
def test_localization_settings_use_first_language_as_default(organizer):
    now = timezone.now()
    event = Event.objects.create(
        organizer=organizer,
        name='Language Order Event',
        slug='language-order-event',
        date_from=now + timedelta(days=10),
        date_to=now + timedelta(days=11),
        currency='USD',
        locale='en',
    )
    event.settings.set('locales', ['en', 'de'])
    event.settings.set('locale', 'de')

    form = EventCommonSettingsForm(obj=event)
    assert isinstance(form.fields['locale'].widget, forms.HiddenInput)
    assert 'bold border' in str(form.fields['locales'].help_text)
    assert form.fields['locales'].widget.attrs['data-ordered-default'] == 'true'
    assert form.fields['locales'].widget.attrs['data-selected-order'] == 'en,de'

    data = form.initial.copy()
    data['timezone'] = data.get('timezone') or 'UTC'
    data['locales'] = ['de', 'en']
    data['locale'] = 'en'
    bound = EventCommonSettingsForm(data=data, obj=event)
    assert bound.is_valid(), bound.errors
    assert bound.cleaned_data['locales'] == ['de', 'en']
    assert bound.cleaned_data['locale'] == 'de'
