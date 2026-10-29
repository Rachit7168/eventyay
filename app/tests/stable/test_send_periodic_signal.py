"""Beat dispatches the single canonical periodic_task signal."""

from eventyay.base.signals import periodic_task as base_periodic_task
from eventyay.common.signals import periodic_task as common_periodic_task
from eventyay.common.tasks import send_periodic_signal


def test_common_periodic_task_is_the_base_signal():
    assert common_periodic_task is base_periodic_task


def test_send_periodic_signal_reaches_receivers_from_either_import():
    received = []

    def common_receiver(signal, sender, **kwargs):
        received.append('common')

    def base_receiver(signal, sender, **kwargs):
        received.append('base')

    common_periodic_task.connect(common_receiver, weak=False)
    base_periodic_task.connect(base_receiver, weak=False)
    try:
        send_periodic_signal()
    finally:
        common_periodic_task.disconnect(common_receiver)
        base_periodic_task.disconnect(base_receiver)

    assert received.count('common') == 1
    assert received.count('base') == 1


def test_failing_receiver_does_not_stop_others():
    received = []

    def failing_receiver(signal, sender, **kwargs):
        raise RuntimeError('boom')

    def later_receiver(signal, sender, **kwargs):
        received.append('later')

    base_periodic_task.connect(failing_receiver, weak=False)
    base_periodic_task.connect(later_receiver, weak=False)
    try:
        send_periodic_signal()
    finally:
        base_periodic_task.disconnect(failing_receiver)
        base_periodic_task.disconnect(later_receiver)

    assert received == ['later']
