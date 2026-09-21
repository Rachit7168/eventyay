import pytest
from django_scopes import scope, scopes_disabled

from eventyay.base.models import Event, TalkQuestion, TalkQuestionTarget, TalkQuestionVariant
from eventyay.person.forms.profile import SpeakerProfileForm


@pytest.mark.django_db
def test_speaker_profile_form_no_duplicate_fields_and_reviewer_visibility(event, speaker):
    """Speaker profile fields come from one form, and reviewers only see visible questions."""
    with scope(event=event):
        visible = TalkQuestion.objects.create(
            event=event,
            question='Visible question',
            variant=TalkQuestionVariant.STRING,
            target=TalkQuestionTarget.SPEAKER,
            is_visible_to_reviewers=True,
        )
        hidden = TalkQuestion.objects.create(
            event=event,
            question='Hidden question',
            variant=TalkQuestionVariant.STRING,
            target=TalkQuestionTarget.SPEAKER,
            is_visible_to_reviewers=False,
        )

        form_orga = SpeakerProfileForm(event=event, user=speaker, for_reviewers=False)
        fields = list(form_orga.fields.keys())
        assert fields.count(f'question_{visible.pk}') == 1
        assert fields.count(f'question_{hidden.pk}') == 1

        form_reviewer = SpeakerProfileForm(event=event, user=speaker, for_reviewers=True)
        fields_reviewer = list(form_reviewer.fields.keys())
        assert f'question_{visible.pk}' in fields_reviewer
        assert f'question_{hidden.pk}' not in fields_reviewer


@pytest.mark.django_db
def test_new_events_do_not_seed_job_title_or_organization(event):
    with scope(event=event):
        assert not TalkQuestion.all_objects.filter(
            event=event,
            import_key__in=['speaker_job_title', 'speaker_organization'],
        ).exists()


@pytest.mark.django_db
def test_event_clone_reuses_matching_import_key(event):
    with scope(event=event):
        TalkQuestion.objects.create(
            event=event,
            question='Shared field',
            variant=TalkQuestionVariant.STRING,
            target=TalkQuestionTarget.SPEAKER,
            import_key='shared_import_key',
            active=False,
        )

    with scopes_disabled():
        dest_event = Event.objects.create(
            name='Dest Event',
            slug='dest',
            organizer=event.organizer,
            date_from=event.date_from,
            date_to=event.date_to,
            timezone=event.timezone,
        )
        with scope(event=dest_event):
            q_dest = TalkQuestion.objects.create(
                event=dest_event,
                question='Destination default',
                variant=TalkQuestionVariant.STRING,
                target=TalkQuestionTarget.SPEAKER,
                import_key='shared_import_key',
                active=True,
            )
        dest_event.copy_data_from(event)

    with scope(event=dest_event):
        q_dest.refresh_from_db()
        assert q_dest.active is False
        assert str(q_dest.question) == 'Shared field'
        assert TalkQuestion.all_objects.filter(event=dest_event, import_key='shared_import_key').count() == 1
