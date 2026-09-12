"""Bounded command-line publisher for PostgreSQL domain outbox records."""
from __future__ import annotations

import logging
import os
import signal
from threading import Event

from services.planning_foundation.database import Database
from .aws_transport import AwsRuntimeConfig, EventBridgeOutboxPublisher


LOGGER = logging.getLogger("hatcommways.runtime.publisher")
STOP = Event()


def run(*, stop: Event = STOP, once: bool = False) -> None:
    config = AwsRuntimeConfig.from_env()
    publisher = EventBridgeOutboxPublisher(
        Database(os.environ["HATCOMMWAYS_DATABASE_URL"]),
        config.session().client("events"),
        config.event_bus_name,
    )
    batch_size = int(os.environ.get("HATCOMMWAYS_OUTBOX_BATCH_SIZE", "10"))
    idle_seconds = float(os.environ.get("HATCOMMWAYS_OUTBOX_IDLE_SECONDS", "2"))
    while not stop.is_set():
        try:
            result = publisher.publish_batch(limit=batch_size)
            if result.selected or result.failed:
                LOGGER.info(
                    "outbox_publish_result selected=%s published=%s failed=%s message_ids=%s",
                    result.selected, result.published, result.failed, ",".join(result.message_ids),
                )
        except Exception:
            LOGGER.exception("outbox_publish_failed")
            result = None
        if once:
            return
        if result is None or result.selected == 0 or result.failed:
            stop.wait(idle_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    run(once=os.environ.get("HATCOMMWAYS_OUTBOX_ONCE") == "1")


if __name__ == "__main__":
    main()
