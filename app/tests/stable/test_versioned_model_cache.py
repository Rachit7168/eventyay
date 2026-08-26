import pickle
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import async_to_sync
from django.core.cache import caches
from django.test.utils import override_settings
from django_scopes import scope

from eventyay.base.models import Room
from eventyay.base.models.cache import _CACHE_LOAD_ERRORS

LOCMEM_PROCESS_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'versioned-model-cache-default',
    },
    'process': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'versioned-model-cache-process',
    },
}


@pytest.mark.django_db
def test_room_pickle_excludes_related_event_settings(room, event):
    """Saving stage config while live attaches Event.settings; that must stay out of cache."""
    with scope(event=event):
        room = Room.objects.select_related('event').get(pk=room.pk)
        _ = room.event.settings
        assert 'event' in room._state.fields_cache

        restored = pickle.loads(pickle.dumps(room))

    assert restored.pk == room.pk
    assert restored._state.fields_cache == {}


@pytest.mark.django_db
@override_settings(CACHES=LOCMEM_PROCESS_CACHE)
def test_process_cache_roundtrip_with_event_settings(room, event):
    with scope(event=event):
        room = Room.objects.select_related('event').get(pk=room.pk)
        _ = room.event.settings

        cache = caches['process']
        cache.clear()
        cache.set(room._cachekey, room, timeout=600)
        cached = cache.get(room._cachekey)

    assert cached is not None
    assert cached.pk == room.pk
    assert cached.version == room.version


@pytest.mark.parametrize('exc_cls', [EOFError, IndexError, ImportError, AttributeError])
@pytest.mark.django_db
@override_settings(CACHES=LOCMEM_PROCESS_CACHE)
def test_refresh_drops_unreadable_process_cache(room, event, exc_cls):
    assert exc_cls in _CACHE_LOAD_ERRORS
    with scope(event=event):
        room = Room.objects.get(pk=room.pk)
        original_version = room.version

        process_cache = MagicMock()
        process_cache.get.side_effect = exc_cls('corrupt')
        process_cache.delete = MagicMock()
        process_cache.set = MagicMock()

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=str(original_version + 1).encode())
        redis.__aenter__ = AsyncMock(return_value=redis)
        redis.__aexit__ = AsyncMock(return_value=None)

        with (
            patch('eventyay.base.models.cache.caches') as caches_mock,
            patch('eventyay.base.models.cache.aredis', return_value=redis),
            patch.object(room, 'refresh_from_db') as refresh_from_db,
        ):
            caches_mock.__getitem__.return_value = process_cache
            room.version = original_version
            async_to_sync(room.refresh_from_db_if_outdated)()

        process_cache.delete.assert_called_once_with(room._cachekey)
        refresh_from_db.assert_called_once()


@pytest.mark.django_db
@override_settings(CACHES=LOCMEM_PROCESS_CACHE)
def test_refresh_drops_cache_entry_without_version(room, event):
    with scope(event=event):
        room = Room.objects.get(pk=room.pk)
        original_version = room.version
        cache = caches['process']
        cache.clear()
        cache.set(room._cachekey, SimpleNamespace(pk=room.pk), timeout=600)

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=str(original_version + 1).encode())
        redis.__aenter__ = AsyncMock(return_value=redis)
        redis.__aexit__ = AsyncMock(return_value=None)

        with (
            patch('eventyay.base.models.cache.aredis', return_value=redis),
            patch.object(room, 'refresh_from_db') as refresh_from_db,
        ):
            room.version = original_version
            async_to_sync(room.refresh_from_db_if_outdated)()

        refresh_from_db.assert_called_once()
        cached = cache.get(room._cachekey)
        # Version-less entries must be discarded; re-cache after a mocked refresh is
        # best-effort and may be skipped if the instance holds unpicklable mocks.
        assert not isinstance(cached, SimpleNamespace)
        if cached is not None:
            assert getattr(cached, 'version', None) is not None
