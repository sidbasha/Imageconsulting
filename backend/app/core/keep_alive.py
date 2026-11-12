"""Keep a free-tier demo host awake by pinging the API's own public /health URL.

Free hosts such as Render's free web service stop an app after about 15 minutes
without inbound traffic. Requests the app makes to itself through its public
address count as inbound traffic, so a ping every ~10 minutes keeps it running.

Off unless IC_KEEP_ALIVE_URL is set. /health does not touch the database, so a
serverless database (e.g. Neon) can still sleep and save its free compute hours.
This is for demos only: a paid instance does not sleep and needs none of this.
"""

import logging
import threading
import urllib.request

logger = logging.getLogger("app.keep_alive")


def ping(url: str, timeout: float = 30) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 (our own https URL)
            return 200 <= response.status < 300
    except OSError as exc:
        logger.warning("keep-alive ping to %s failed: %s", url, exc)
        return False


def start(url: str, minutes: float) -> threading.Event:
    """Ping `url` every `minutes` in a daemon thread. Set the returned event to stop."""
    stop = threading.Event()

    def loop() -> None:
        # Wait first: the app has just started, so it is awake now.
        while not stop.wait(minutes * 60):
            ping(url)

    threading.Thread(target=loop, name="keep-alive", daemon=True).start()
    logger.info("keep-alive: pinging %s every %s minutes", url, minutes)
    return stop
