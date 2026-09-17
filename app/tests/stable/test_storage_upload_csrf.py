import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from eventyay.storage.views import _enforce_csrf


def test_session_upload_csrf_rejects_missing_token():
    request = RequestFactory().post("/storage/evt/upload/")
    with pytest.raises(PermissionDenied, match="CSRF verification failed"):
        _enforce_csrf(request)


@pytest.mark.django_db
def test_session_upload_success_with_csrf_token(client, event, organizer_client):
    # organizer_client is already authenticated as a user with event permissions
    from django.urls import reverse
    from django.core.files.uploadedfile import SimpleUploadedFile

    # Make a GET request to obtain the CSRF cookie
    organizer_client.get("/")
    csrftoken = organizer_client.cookies["csrftoken"].value

    file = SimpleUploadedFile("test.png", b"file_content", content_type="image/png")
    upload_url = reverse("storage:upload", kwargs={"event_id": event.id})
    
    response = organizer_client.post(
        upload_url,
        data={"file": file},
        HTTP_X_CSRFTOKEN=csrftoken,
    )
    
    assert response.status_code == 201
    assert "url" in response.json()
