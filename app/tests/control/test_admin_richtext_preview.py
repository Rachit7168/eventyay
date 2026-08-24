import json

from django.test import RequestFactory

from eventyay.common.sanitizers import sanitize_rich_text
from eventyay.control.views.global_settings import AdminRichTextPreviewView


def test_admin_richtext_preview_single_content():
    request = RequestFactory().post('/', {'content': '<p>Hello</p>'})
    response = AdminRichTextPreviewView().post(request)
    assert response.status_code == 200
    payload = json.loads(response.content)
    assert payload['html'] == sanitize_rich_text('<p>Hello</p>')


def test_admin_richtext_preview_localized_content():
    request = RequestFactory().post(
        '/',
        {
            'content_en': '<p>English</p>',
            'content_de': '<p><script>alert(1)</script>German</p>',
        },
    )
    response = AdminRichTextPreviewView().post(request)
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['previews']['en'] == sanitize_rich_text('<p>English</p>')
    assert data['previews']['de'] == sanitize_rich_text('<p><script>alert(1)</script>German</p>')


def test_admin_richtext_preview_missing_content():
    request = RequestFactory().post('/', {})
    response = AdminRichTextPreviewView().post(request)
    assert response.status_code == 400
