import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from eventyay.storage.views import _enforce_csrf


def test_session_upload_csrf_rejects_missing_token():
    request = RequestFactory().post("/storage/evt/upload/")
    with pytest.raises(PermissionDenied, match="CSRF verification failed"):
        _enforce_csrf(request)
