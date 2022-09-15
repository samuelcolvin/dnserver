import os
import signal
from pathlib import Path
from time import sleep

from .main import DNSServer, logger

__all__ = ('cli',)


def handle_sig(signum, frame):
    logger.info('pid=%d, got signal: %s, stopping...', os.getpid(), signal.Signals(signum).name)
    exit(0)


def cli():
    signal.signal(signal.SIGTERM, handle_sig)
    signal.signal(signal.SIGINT, handle_sig)

    port = int(os.getenv('PORT', 53))
    upstream = os.getenv('UPSTREAM', '8.8.8.8')
    zones_file = os.getenv('ZONE_FILE', '/zones/zones.txt')
    zone = Path(zones_file).read_text()

    server = DNSServer(port, zone, upstream)
    server.start()

    try:
        while server.is_running:
            sleep(0.1)
    finally:
        logger.info('stopping DNS server')
        server.stop()
