import pytest
from django_scopes import scope

from eventyay.base.models import Answer, AnswerOption, SpeakerProfile, User
from eventyay.base.models import TalkQuestion as Question
from eventyay.base.models import TalkQuestionVariant as QuestionVariant
from eventyay.base.models.question import TalkQuestionRequired as QuestionRequired
from eventyay.base.models.question import TalkQuestionTarget
from eventyay.base.models import Submission
from eventyay.base.models.submission import SubmissionStates
from eventyay.base.models.type import SubmissionType
from eventyay.base.services.talkimport import (
    ImportExecutionError,
    _apply_new_question_mappings,
    _import_speaker_row,
    _import_submission_row,
    _load_mapped_questions,
    _set_question_answer,
)
from eventyay.orga.forms.importers import SpeakerImportProcessForm


def _speaker_settings(**overrides):
    settings = {
        'email': 'csv:email',
        'full_name': 'csv:name',
    }
    settings.update(overrides)
    return settings


def _speaker_row(**overrides):
    row = {
        'email': 'imported.speaker@example.org',
        'name': 'Ada Lovelace',
    }
    row.update(overrides)
    return row


def _choice_cache(question):
    return {
        question.pk: (
            question,
            {str(option.answer).strip().casefold(): option for option in question.options.all()},
        )
    }


def _create_question(event, *, question, variant, target, required=QuestionRequired.OPTIONAL, active=True):
    return Question.objects.create(
        event=event,
        question=question,
        variant=variant,
        target=target,
        question_required=required,
        active=active,
    )


@pytest.mark.django_db
def test_speaker_import_form_allows_unmapped_required_question(event):
    with scope(event=event):
        question = _create_question(
            event,
            question='T-shirt size',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SPEAKER,
            required=QuestionRequired.REQUIRED,
        )
        form = SpeakerImportProcessForm(
            data={
                'email': 'csv:Email',
                'full_name': 'csv:Name',
                f'question_{question.pk}': '',
            },
            headers=['Email', 'Name'],
            event=event,
        )

        assert form.fields[f'question_{question.pk}'].required is False
        assert form.is_valid(), form.errors
        assert form.cleaned_data[f'question_{question.pk}'] == ''


@pytest.mark.django_db
def test_load_mapped_questions_keeps_active_speaker_targets_only(event):
    with scope(event=event):
        speaker_question = _create_question(
            event,
            question='Favourite color',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SPEAKER,
        )
        submission_question = _create_question(
            event,
            question='Session level',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SUBMISSION,
        )
        inactive_submission_question = _create_question(
            event,
            question='Inactive session field',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SUBMISSION,
            active=False,
        )
        inactive_speaker_question = _create_question(
            event,
            question='Hidden speaker field',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SPEAKER,
            active=False,
        )
        settings = {
            f'question_{speaker_question.pk}': 'csv:Color',
            f'question_{submission_question.pk}': 'csv:Session',
            f'question_{inactive_submission_question.pk}': 'csv:Inactive',
            f'question_{inactive_speaker_question.pk}': 'csv:Hidden',
        }

        mappings, cache = _load_mapped_questions(event, settings, target=TalkQuestionTarget.SPEAKER)

        assert mappings == [(speaker_question.pk, 'csv:Color')]
        assert set(cache) == {speaker_question.pk}


@pytest.mark.django_db
def test_import_speaker_row_saves_mapped_choice_answer(event, user):
    with scope(event=event):
        question = _create_question(
            event,
            question='How much do you like green?',
            variant=QuestionVariant.CHOICES,
            target=TalkQuestionTarget.SPEAKER,
        )
        option = AnswerOption.objects.create(question=question, answer='very')
        AnswerOption.objects.create(question=question, answer='incredibly')
        caches = {
            'question_mappings': [(question.pk, 'csv:color')],
            'question_cache': _choice_cache(question),
        }

        created = _import_speaker_row(
            event,
            _speaker_settings(),
            _speaker_row(color='very'),
            user,
            caches=caches,
        )

        assert created is True
        answer = Answer.objects.get(question=question, person__email='imported.speaker@example.org')
        assert list(answer.options.all()) == [option]


@pytest.mark.django_db
def test_import_speaker_row_rejects_unknown_choice_value(event, user):
    with scope(event=event):
        question = _create_question(
            event,
            question='How much do you like green?',
            variant=QuestionVariant.CHOICES,
            target=TalkQuestionTarget.SPEAKER,
        )
        AnswerOption.objects.create(question=question, answer='very')
        caches = {
            'question_mappings': [(question.pk, 'csv:color')],
            'question_cache': _choice_cache(question),
        }

        with pytest.raises(ImportExecutionError, match='Invalid answer'):
            _import_speaker_row(
                event,
                _speaker_settings(),
                _speaker_row(color='purple'),
                user,
                caches=caches,
            )

        assert not SpeakerProfile.objects.filter(event=event, user__email='imported.speaker@example.org').exists()
        assert not Answer.objects.filter(question=question).exists()
        assert not User.objects.filter(email='imported.speaker@example.org').exists()


@pytest.mark.django_db
def test_set_question_answer_requires_speaker_owner(event):
    with scope(event=event):
        question = _create_question(
            event,
            question='Favourite color',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SPEAKER,
        )
        _set_question_answer(question.pk, 'green', event=event)

        assert not Answer.objects.filter(question=question).exists()


@pytest.mark.django_db
def test_set_question_answer_skips_submission_question_without_submission(event, user):
    with scope(event=event):
        question = _create_question(
            event,
            question='Session level',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SUBMISSION,
        )
        _set_question_answer(question.pk, 'beginner', person=user, event=event)

        assert not Answer.objects.filter(question=question).exists()


@pytest.mark.django_db
def test_speaker_import_form_offers_create_for_unmapped_column(event):
    with scope(event=event):
        form = SpeakerImportProcessForm(
            headers=['Email', 'Name', 'T-shirt size'],
            event=event,
        )

        assert 'create_question_enabled_t-shirt-size' in form.fields
        assert 'create_question_enabled_email' not in form.fields
        assert form.fields['create_question_enabled_t-shirt-size'].initial is False
        assert len(form.new_question_rows) == 1
        assert form.new_question_rows[0]['header'] == 'T-shirt size'


@pytest.mark.django_db
def test_speaker_import_form_collects_new_question_specs(event):
    with scope(event=event):
        form = SpeakerImportProcessForm(
            data={
                'email': 'csv:Email',
                'full_name': 'csv:Name',
                'create_question_enabled_t-shirt-size': True,
                'create_question_header_t-shirt-size': 'T-shirt size',
                'create_question_label_t-shirt-size': 'Shirt size',
                'create_question_variant_t-shirt-size': QuestionVariant.NUMBER,
            },
            headers=['Email', 'Name', 'T-shirt size'],
            event=event,
        )

        assert form.is_valid(), form.errors
        assert form.cleaned_data['new_questions'] == [
            {
                'header': 'T-shirt size',
                'label': 'Shirt size',
                'variant': QuestionVariant.NUMBER,
                'mapping': 'csv:T-shirt size',
            }
        ]


@pytest.mark.django_db
def test_import_speaker_row_creates_and_maps_new_question(event, user):
    with scope(event=event):
        settings = _speaker_settings(
            new_questions=[
                {
                    'header': 'color',
                    'label': 'Favourite color',
                    'variant': QuestionVariant.STRING,
                    'mapping': 'csv:color',
                }
            ]
        )
        mappings, cache = _load_mapped_questions(event, settings, target=TalkQuestionTarget.SPEAKER)
        caches = {'import_questions': {}, 'import_question_positions': {}}
        mappings, cache = _apply_new_question_mappings(
            event,
            settings,
            mappings,
            cache,
            target=TalkQuestionTarget.SPEAKER,
            caches=caches,
        )
        caches['question_mappings'] = mappings
        caches['question_cache'] = cache

        created = _import_speaker_row(event, settings, _speaker_row(color='green'), user, caches=caches)

        assert created is True
        question = Question.objects.get(event=event, target=TalkQuestionTarget.SPEAKER)
        assert str(question.question) == 'Favourite color'
        assert question.variant == QuestionVariant.STRING
        answer = Answer.objects.get(question=question, person__email='imported.speaker@example.org')
        assert answer.answer == 'green'


@pytest.mark.django_db
def test_apply_new_question_mappings_reuses_existing_question(event):
    with scope(event=event):
        question = _create_question(
            event,
            question='Favourite color',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SPEAKER,
        )
        settings = {
            'new_questions': [
                {
                    'header': 'color',
                    'label': 'Favourite color',
                    'variant': QuestionVariant.TEXT,
                    'mapping': 'csv:color',
                }
            ]
        }
        mappings, cache = _apply_new_question_mappings(
            event,
            settings,
            [],
            {},
            target=TalkQuestionTarget.SPEAKER,
            caches={'import_questions': {}, 'import_question_positions': {}},
        )

        assert mappings == [(question.pk, 'csv:color')]
        assert Question.objects.filter(event=event, target=TalkQuestionTarget.SPEAKER).count() == 1
        question.refresh_from_db()
        assert question.variant == QuestionVariant.STRING


@pytest.mark.django_db
def test_import_submission_row_deletes_new_submission_on_invalid_choice(event, user):
    with scope(event=event):
        sub_type = SubmissionType.objects.create(event=event, name='Talk')
        question = _create_question(
            event,
            question='Session level',
            variant=QuestionVariant.CHOICES,
            target=TalkQuestionTarget.SUBMISSION,
        )
        AnswerOption.objects.create(question=question, answer='beginner')
        caches = {
            'submission_types': [sub_type],
            'tracks': [],
            'rooms': [],
            'valid_states': {choice[0] for choice in SubmissionStates.get_choices()},
            'default_sub_type': sub_type,
            'question_mappings': [(question.pk, 'csv:level')],
            'question_cache': _choice_cache(question),
        }

        with pytest.raises(ImportExecutionError, match='Invalid answer'):
            _import_submission_row(
                event,
                {'title': 'csv:title'},
                {'title': 'A new talk', 'level': 'unknown'},
                user,
                caches=caches,
            )

        assert not Submission.objects.filter(event=event, title='A new talk').exists()
        assert not Answer.objects.filter(question=question).exists()
