import pytest
from django_scopes import scope

from eventyay.base.models import Answer, AnswerOption, Submission
from eventyay.base.models import TalkQuestion as Question
from eventyay.base.models import TalkQuestionVariant as QuestionVariant
from eventyay.base.models.question import TalkQuestionRequired as QuestionRequired
from eventyay.base.models.question import TalkQuestionTarget
from eventyay.base.models.submission import SubmissionStates
from eventyay.base.models.type import SubmissionType
from eventyay.base.services.talkimport import (
    ImportExecutionError,
    _apply_new_question_mappings,
    _import_submission_row,
    _load_mapped_questions,
)
from eventyay.orga.forms.importers import SessionImportProcessForm


def _create_question(event, *, question, variant, target, required=QuestionRequired.OPTIONAL, active=True):
    return Question.objects.create(
        event=event,
        question=question,
        variant=variant,
        target=target,
        question_required=required,
        active=active,
    )


def _choice_cache(question):
    return {
        question.pk: (
            question,
            {str(option.answer).strip().casefold(): option for option in question.options.all()},
        )
    }


def _session_caches(event, **overrides):
    sub_type = SubmissionType.objects.create(event=event, name='Talk')
    caches = {
        'submission_types': [sub_type],
        'tracks': [],
        'rooms': [],
        'valid_states': {choice[0] for choice in SubmissionStates.get_choices()},
        'default_sub_type': sub_type,
        'question_mappings': [],
        'question_cache': {},
        'import_questions': {},
        'import_question_positions': {},
    }
    caches.update(overrides)
    return caches


@pytest.mark.django_db
def test_session_import_form_allows_unmapped_required_question(event):
    with scope(event=event):
        question = _create_question(
            event,
            question='Session level',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SUBMISSION,
            required=QuestionRequired.REQUIRED,
        )
        form = SessionImportProcessForm(
            data={
                'title': 'csv:Title',
                f'question_{question.pk}': '',
            },
            headers=['Title'],
            event=event,
        )

        assert form.fields[f'question_{question.pk}'].required is False
        assert form.is_valid(), form.errors
        assert form.cleaned_data[f'question_{question.pk}'] == ''


@pytest.mark.django_db
def test_session_import_form_offers_create_for_unmapped_column(event):
    with scope(event=event):
        form = SessionImportProcessForm(
            headers=['Proposal title', 'Audience takeaway'],
            event=event,
        )

        assert form.fields['title'].initial == 'csv:Proposal title'
        assert 'create_question_enabled_audience-takeaway' in form.fields
        assert form.fields['create_question_enabled_audience-takeaway'].initial is True
        assert len(form.new_question_rows) == 1
        assert form.new_question_rows[0]['header'] == 'Audience takeaway'


@pytest.mark.django_db
def test_session_import_form_maps_export_columns(event):
    with scope(event=event):
        form = SessionImportProcessForm(
            headers=['Proposal title', 'Proposal state', 'Speaker IDs', 'Speaker names', 'Duration'],
            event=event,
        )

        assert form.fields['title'].initial == 'csv:Proposal title'
        assert form.fields['state'].initial == 'csv:Proposal state'
        assert form.fields['linked_speakers'].initial == 'csv:Speaker IDs'
        assert form.fields['speakers'].initial == 'csv:Speaker names'
        assert form.fields['duration'].initial == 'csv:Duration'
        assert form.new_question_rows == []


@pytest.mark.django_db
def test_session_import_form_maps_matching_dest_question_by_name(event):
    with scope(event=event):
        question = _create_question(
            event,
            question='Audience takeaway',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SUBMISSION,
        )
        form = SessionImportProcessForm(
            headers=['Proposal title', 'Audience takeaway'],
            event=event,
            initial={f'question_{question.pk}': 'csv:Old source header'},
        )

        assert form.fields[f'question_{question.pk}'].initial == 'csv:Audience takeaway'
        assert all(row['header'] != 'Audience takeaway' for row in form.new_question_rows)


@pytest.mark.django_db
def test_session_import_form_skips_reserved_export_headers(event):
    with scope(event=event):
        form = SessionImportProcessForm(
            headers=[
                'Proposal title',
                'ID',
                'Speaker IDs',
                'Speaker names',
                'Pending proposal state',
                'Created',
                'Slot Count',
                'Session image',
                'Median score',
                'Average (mean) score',
                'Resources',
                'Start (date)',
                'Start (time)',
                'End (date)',
                'End (time)',
            ],
            event=event,
        )

        assert form.new_question_rows == []


@pytest.mark.django_db
def test_session_import_form_does_not_auto_create_when_dest_has_questions(event):
    with scope(event=event):
        _create_question(
            event,
            question='Audience takeaway',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SUBMISSION,
        )
        form = SessionImportProcessForm(
            headers=['Proposal title', 'T-shirt size'],
            event=event,
        )

        assert form.fields['create_question_enabled_t-shirt-size'].initial is False


@pytest.mark.django_db
def test_import_submission_row_saves_mapped_question_answer(event, user):
    with scope(event=event):
        question = _create_question(
            event,
            question='Audience takeaway',
            variant=QuestionVariant.STRING,
            target=TalkQuestionTarget.SUBMISSION,
        )
        caches = _session_caches(
            event,
            question_mappings=[(question.pk, 'csv:takeaway')],
            question_cache={question.pk: (question, None)},
        )

        created = _import_submission_row(
            event,
            {'title': 'csv:title'},
            {'title': 'A mapped talk', 'takeaway': 'Leave with a plan'},
            user,
            caches=caches,
        )

        assert created is True
        answer = Answer.objects.get(question=question, submission__title='A mapped talk')
        assert answer.answer == 'Leave with a plan'


@pytest.mark.django_db
def test_import_submission_row_creates_and_maps_new_question(event, user):
    with scope(event=event):
        settings = {
            'title': 'csv:title',
            'new_questions': [
                {
                    'header': 'takeaway',
                    'label': 'Audience takeaway',
                    'variant': QuestionVariant.STRING,
                    'mapping': 'csv:takeaway',
                }
            ],
        }
        mappings, cache = _load_mapped_questions(event, settings, target=TalkQuestionTarget.SUBMISSION)
        caches = _session_caches(event)
        mappings, cache = _apply_new_question_mappings(
            event,
            settings,
            mappings,
            cache,
            target=TalkQuestionTarget.SUBMISSION,
            caches=caches,
        )
        caches['question_mappings'] = mappings
        caches['question_cache'] = cache

        created = _import_submission_row(
            event,
            settings,
            {'title': 'A created-field talk', 'takeaway': 'Ship the feature'},
            user,
            caches=caches,
        )

        assert created is True
        question = Question.objects.get(event=event, target=TalkQuestionTarget.SUBMISSION)
        assert str(question.question) == 'Audience takeaway'
        answer = Answer.objects.get(question=question, submission__title='A created-field talk')
        assert answer.answer == 'Ship the feature'


@pytest.mark.django_db
def test_import_submission_row_rejects_unknown_choice_and_cleans_up(event, user):
    with scope(event=event):
        question = _create_question(
            event,
            question='Session level',
            variant=QuestionVariant.CHOICES,
            target=TalkQuestionTarget.SUBMISSION,
        )
        AnswerOption.objects.create(question=question, answer='beginner')
        caches = _session_caches(
            event,
            question_mappings=[(question.pk, 'csv:level')],
            question_cache=_choice_cache(question),
        )

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
