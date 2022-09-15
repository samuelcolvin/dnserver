import os
import signal
from pathlib import Path
from time import sleep

from .main import DNSServer, logger

__all__ = ('cli',)


def handle_sig(signum, frame):  # pragma: no cover
    logger.info('pid=%d, got signal: %s, stopping...', os.getpid(), signal.Signals(signum).name)
    raise KeyboardInterrupt


def cli():
    signal.signal(signal.SIGTERM, handle_sig)
    signal.signal(signal.SIGINT, handle_sig)

    port = os.getenv('PORT', 53)
    upstream = os.getenv('UPSTREAM', None)
    zones_file = os.getenv('ZONE_FILE', '/zones/zones.txt')
    zones_text = Path(zones_file).read_text()

    server = DNSServer(zones_text, port=port, upstream=upstream)
    server.start()

    try:
        while server.is_running:
            sleep(0.1)
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        logger.info('stopping DNS server')
        server.stop()
