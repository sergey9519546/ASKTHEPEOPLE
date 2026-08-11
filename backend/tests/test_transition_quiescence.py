"""Fail-closed checks used before backing up the single-host demo."""

from __future__ import annotations

from scripts.assert_celery_quiescent import (
    evaluate_consumers_stopped,
    evaluate_quiescence,
    evaluate_stable_quiescence,
    quiesce_consumers,
)


class _Inspector:
    def __init__(self, snapshots):
        self._snapshots = snapshots

    def active(self):
        return self._snapshots["active"]

    def reserved(self):
        return self._snapshots["reserved"]

    def scheduled(self):
        return self._snapshots["scheduled"]

    def active_queues(self):
        return self._snapshots.get("active_queues")


class _SequenceInspector:
    def __init__(self, snapshots):
        self._snapshots = snapshots

    def active(self):
        return self._snapshots["active"].pop(0)

    def reserved(self):
        return self._snapshots["reserved"].pop(0)

    def scheduled(self):
        return self._snapshots["scheduled"].pop(0)


class _Broker:
    def __init__(self, *, queued=0, unacked=0):
        self.queued = queued
        self.unacked = unacked

    def llen(self, _queue):
        return self.queued

    def hlen(self, _key):
        return self.unacked

    def zcard(self, _key):
        return self.unacked


class _Control:
    def __init__(self, *, fail_cancel: bool = False):
        self.fail_cancel = fail_cancel
        self.cancelled: list[str] = []
        self.restored: list[str] = []

    def cancel_consumer(self, queue, **_kwargs):
        self.cancelled.append(queue)
        if self.fail_cancel:
            raise RuntimeError("provider detail must stay private")

    def add_consumer(self, queue, **_kwargs):
        self.restored.append(queue)


def test_quiescence_requires_empty_replies_for_every_queue() -> None:
    inspector = _Inspector(
        {
            "active": {"worker@demo": []},
            "reserved": {"worker@demo": []},
            "scheduled": {"worker@demo": []},
        }
    )

    assert evaluate_quiescence(inspector) == (0, "celery_quiescent")


def test_quiescence_rejects_live_work() -> None:
    inspector = _Inspector(
        {
            "active": {"worker@demo": [{"id": "task-1"}]},
            "reserved": {"worker@demo": []},
            "scheduled": {"worker@demo": []},
        }
    )

    assert evaluate_quiescence(inspector) == (78, "celery_not_quiescent")


def test_quiescence_rejects_missing_or_malformed_replies() -> None:
    for snapshot in (None, {}, {"worker@demo": None}):
        inspector = _Inspector(
            {
                "active": snapshot,
                "reserved": {"worker@demo": []},
                "scheduled": {"worker@demo": []},
            }
        )

        assert evaluate_quiescence(inspector) == (
            78,
            "celery_quiescence_unverified",
        )


def test_stable_quiescence_requires_two_empty_snapshots_and_empty_broker() -> None:
    empty = {"worker@demo": []}
    inspector = _SequenceInspector(
        {
            "active": [empty, empty],
            "reserved": [empty, empty],
            "scheduled": [empty, empty],
        }
    )

    assert evaluate_stable_quiescence(
        inspector,
        _Broker(),
        ("celery",),
        pause=lambda _seconds: None,
    ) == (0, "celery_quiescent")


def test_stable_quiescence_rejects_broker_or_second_snapshot_work() -> None:
    empty = {"worker@demo": []}
    active = {"worker@demo": [{"id": "task-2"}]}
    for inspector, broker in (
        (
            _SequenceInspector(
                {
                    "active": [empty, empty],
                    "reserved": [empty, empty],
                    "scheduled": [empty, empty],
                }
            ),
            _Broker(queued=1),
        ),
        (
            _SequenceInspector(
                {
                    "active": [empty, active],
                    "reserved": [empty, empty],
                    "scheduled": [empty, empty],
                }
            ),
            _Broker(),
        ),
    ):
        assert evaluate_stable_quiescence(
            inspector,
            broker,
            ("celery",),
            pause=lambda _seconds: None,
        ) == (78, "celery_not_quiescent")


def test_consumer_stop_proof_requires_every_worker_to_drop_the_queue() -> None:
    stopped = _Inspector(
        {
            "active_queues": {"worker@demo": []},
        }
    )
    consuming = _Inspector(
        {
            "active_queues": {
                "worker@demo": [{"name": "celery"}],
            },
        }
    )
    missing = _Inspector({"active_queues": None})

    assert evaluate_consumers_stopped(stopped, ("celery",)) == (
        0,
        "celery_consumers_stopped",
    )
    assert evaluate_consumers_stopped(consuming, ("celery",)) == (
        78,
        "celery_not_quiescent",
    )
    assert evaluate_consumers_stopped(missing, ("celery",)) == (
        78,
        "celery_quiescence_unverified",
    )


def test_post_cancel_failure_restores_every_consumer() -> None:
    empty = {"worker@demo": []}
    inspector = _SequenceInspector(
        {
            # Two pre-cancel empty samples, followed by a malformed
            # post-cancel sample that must trigger restoration.
            "active": [empty, empty, None],
            "reserved": [empty, empty],
            "scheduled": [empty, empty],
        }
    )
    inspector.active_queues = lambda: empty
    control = _Control()

    assert quiesce_consumers(
        control,
        inspector,
        _Broker(),
        ("celery",),
        pause=lambda _seconds: None,
    ) == (78, "celery_quiescence_unverified")
    assert control.cancelled == ["celery"]
    assert control.restored == ["celery"]


def test_cancel_exception_restores_consumer_and_fails_closed() -> None:
    empty = {"worker@demo": []}
    inspector = _SequenceInspector(
        {
            "active": [empty, empty],
            "reserved": [empty, empty],
            "scheduled": [empty, empty],
        }
    )
    control = _Control(fail_cancel=True)

    assert quiesce_consumers(
        control,
        inspector,
        _Broker(),
        ("celery",),
        pause=lambda _seconds: None,
    ) == (78, "celery_quiescence_unverified")
    assert control.restored == ["celery"]
