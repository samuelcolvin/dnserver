from __future__ import annotations as _annotations

import argparse
import os
import signal
import sys
from time import sleep

from .main import DNSServer, logger
from .version import VERSION

__all__ = ('cli',)


def handle_sig(signum, frame):  # pragma: no cover
    logger.info('pid=%d, got signal: %s, stopping...', os.getpid(), signal.Signals(signum).name)
    raise KeyboardInterrupt


HELP_TEXT = f"""\
Simple DNS server written in python for use in development and testing.

See https://github.com/samuelcolvin/dnserver for more information.

V{VERSION}
"""


def cli_logic(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog='dnserver', description=HELP_TEXT, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'zones_file',
        nargs='?',
        help='TOML file containing zones info, if omitted will use DNSERVER_ZONE_FILE env var',
    )
    parser.add_argument('--port', help='Port to run on, if omitted will use DNSERVER_PORT env var, or 53')
    parser.add_argument(
        '--upstream',
        help=(
            'Upstream DNS server to use if no record is found in the zone TOML file, '
            'if omitted will use DNSERVER_UPSTREAM env var, or 1.1.1.1'
        ),
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s v{VERSION}')
    parsed_args = parser.parse_args(args)

    port = parsed_args.port or os.getenv('DNSERVER_PORT', None)
    upstream = parsed_args.upstream or os.getenv('DNSERVER_UPSTREAM', None)
    zones_file = parsed_args.zones_file or os.getenv('DNSERVER_ZONE_FILE', None)
    if zones_file is None:
        print('no zones file specified, use --help for more information', file=sys.stderr)
        return 1

    signal.signal(signal.SIGTERM, handle_sig)
    signal.signal(signal.SIGINT, handle_sig)

    server = DNSServer(zones_file, port=port, upstream=upstream)
    server.start()

    try:
        while server.is_running:
            sleep(0.1)
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        logger.info('stopping DNS server')
        server.stop()

    return 0


def cli():  # pragma: no cover
    exit(cli_logic(sys.argv[1:]))
