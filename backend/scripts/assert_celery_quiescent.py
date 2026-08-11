"""Fail closed unless every reachable Celery worker reports no queued work."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any


def evaluate_quiescence(inspector: Any) -> tuple[int, str]:
    for method_name in ("active", "reserved", "scheduled"):
        try:
            snapshot = getattr(inspector, method_name)()
        except Exception:
            return 78, "celery_quiescence_unverified"
        if not isinstance(snapshot, dict) or not snapshot:
            return 78, "celery_quiescence_unverified"
        for tasks in snapshot.values():
            if not isinstance(tasks, list):
                return 78, "celery_quiescence_unverified"
            if tasks:
                return 78, "celery_not_quiescent"
    return 0, "celery_quiescent"


def _evaluate_broker(broker: Any, queue_names: tuple[str, ...]) -> tuple[int, str]:
    try:
        depths = [broker.llen(queue) for queue in queue_names]
        depths.extend((broker.hlen("unacked"), broker.zcard("unacked_index")))
    except Exception:
        return 78, "celery_quiescence_unverified"
    if any(type(depth) is not int or depth < 0 for depth in depths):
        return 78, "celery_quiescence_unverified"
    if any(depth for depth in depths):
        return 78, "celery_not_quiescent"
    return 0, "celery_quiescent"


def evaluate_consumers_stopped(
    inspector: Any,
    queue_names: tuple[str, ...],
) -> tuple[int, str]:
    try:
        snapshot = inspector.active_queues()
    except Exception:
        return 78, "celery_quiescence_unverified"
    if not isinstance(snapshot, dict) or not snapshot:
        return 78, "celery_quiescence_unverified"
    expected = set(queue_names)
    for queues in snapshot.values():
        if not isinstance(queues, list):
            return 78, "celery_quiescence_unverified"
        for queue in queues:
            if not isinstance(queue, dict) or not isinstance(queue.get("name"), str):
                return 78, "celery_quiescence_unverified"
            if queue["name"] in expected:
                return 78, "celery_not_quiescent"
    return 0, "celery_consumers_stopped"


def evaluate_stable_quiescence(
    inspector: Any,
    broker: Any,
    queue_names: tuple[str, ...],
    *,
    pause=time.sleep,
) -> tuple[int, str]:
    if not queue_names:
        return 78, "celery_quiescence_unverified"
    for attempt in range(2):
        worker_status = evaluate_quiescence(inspector)
        if worker_status != (0, "celery_quiescent"):
            return worker_status
        broker_status = _evaluate_broker(broker, queue_names)
        if broker_status != (0, "celery_quiescent"):
            return broker_status
        if attempt == 0:
            pause(1.0)
    return 0, "celery_quiescent"


def _restore_consumers(control: Any, queue_names: tuple[str, ...]) -> None:
    for queue_name in queue_names:
        try:
            control.add_consumer(
                queue_name,
                reply=True,
                timeout=5.0,
            )
        except Exception:
            # Recovery is best effort; the caller still fails closed with a
            # stable diagnostic and never exposes broker/provider details.
            pass


def quiesce_consumers(
    control: Any,
    inspector: Any,
    broker: Any,
    queue_names: tuple[str, ...],
    *,
    pause=time.sleep,
) -> tuple[int, str]:
    initial_status = evaluate_stable_quiescence(
        inspector,
        broker,
        queue_names,
        pause=pause,
    )
    if initial_status != (0, "celery_quiescent"):
        return initial_status

    cancellation_attempted = False
    try:
        for queue_name in queue_names:
            cancellation_attempted = True
            control.cancel_consumer(
                queue_name,
                reply=True,
                timeout=5.0,
            )

        consumer_status = (78, "celery_not_quiescent")
        for attempt in range(5):
            consumer_status = evaluate_consumers_stopped(
                inspector,
                queue_names,
            )
            if consumer_status == (0, "celery_consumers_stopped"):
                break
            if consumer_status == (78, "celery_quiescence_unverified"):
                break
            if attempt < 4:
                pause(1.0)
        if consumer_status != (0, "celery_consumers_stopped"):
            _restore_consumers(control, queue_names)
            return consumer_status

        final_status = evaluate_stable_quiescence(
            inspector,
            broker,
            queue_names,
            pause=pause,
        )
        if final_status != (0, "celery_quiescent"):
            _restore_consumers(control, queue_names)
            return final_status
        return final_status
    except Exception:
        if cancellation_attempted:
            _restore_consumers(control, queue_names)
        return 78, "celery_quiescence_unverified"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker-only", action="store_true")
    args = parser.parse_args()
    try:
        from redis import Redis

        from app.celery_app import broker_url, celery_app

        broker = Redis.from_url(
            broker_url,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        queue_names = tuple(celery_app.amqp.queues.keys()) or ("celery",)
        if args.broker_only:
            status, message = _evaluate_broker(broker, queue_names)
            if status == 0:
                message = "celery_broker_quiescent"
        else:
            control = celery_app.control
            inspector = control.inspect(timeout=5.0)
            status, message = quiesce_consumers(
                control,
                inspector,
                broker,
                queue_names,
            )
    except Exception:
        status, message = 78, "celery_quiescence_unverified"
    print(message, file=sys.stdout if status == 0 else sys.stderr)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
