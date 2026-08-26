from eventyay.base.services.room_creation_gate import (
    newly_added_server_backed_room_modules,
)


def test_newly_added_detects_first_server_backed_module():
    old = [{"type": "chat.native"}]
    new = [{"type": "chat.native"}, {"type": "call.bigbluebutton"}]
    added = newly_added_server_backed_room_modules(old, new)
    assert [m["type"] for m in added] == ["call.bigbluebutton"]


def test_newly_added_ignores_existing_server_backed_type():
    old = [{"type": "call.bigbluebutton"}]
    new = [{"type": "call.bigbluebutton", "config": {"updated": True}}]
    assert newly_added_server_backed_room_modules(old, new) == []


def test_newly_added_detects_second_module_of_same_type():
    old = [{"type": "call.bigbluebutton", "config": {"id": "a"}}]
    new = [
        {"type": "call.bigbluebutton", "config": {"id": "a"}},
        {"type": "call.bigbluebutton", "config": {"id": "b"}},
    ]
    added = newly_added_server_backed_room_modules(old, new)
    assert len(added) == 1
    assert added[0]["config"]["id"] == "b"


def test_newly_added_detects_additional_distinct_server_backed_type():
    old = [{"type": "call.bigbluebutton"}]
    new = [{"type": "call.bigbluebutton"}, {"type": "call.jitsi"}]
    added = newly_added_server_backed_room_modules(old, new)
    assert [m["type"] for m in added] == ["call.jitsi"]
