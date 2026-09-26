import pytest
from django_scopes import scope

from eventyay.base.models import Answer, AnswerOption, SpeakerProfile, User
from eventyay.base.models import TalkQuestion as Question
from eventyay.base.models import TalkQuestionVariant as QuestionVariant
from eventyay.base.models.question import TalkQuestionRequired as QuestionRequired
from eventyay.base.models.question import TalkQuestionTarget
from eventyay.base.services.talkimport import (
    ImportExecutionError,
    _import_speaker_row,
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
