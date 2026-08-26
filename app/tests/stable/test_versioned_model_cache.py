import pickle

import pytest
from django.core.cache import caches
from django.test.utils import override_settings
from django_scopes import scope

from eventyay.base.models import Room

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
