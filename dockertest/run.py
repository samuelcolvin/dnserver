#!/usr/bin/env python3.6
import asyncio
import logging
from pathlib import Path
from time import sleep

import aiodns
from aiodns.error import DNSError

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%H:%M:%S'))

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


async def query(resolver, *args):
    try:
        return await resolver.query(*args)
    except DNSError as e:
        return f'{e.__class__.__name__}: {e}'


async def main(loop):
    resolver = aiodns.DNSResolver(loop=loop)
    for domain in ('example.com', 'google.com', 'ns', 'test'):
        logger.info('%s %s:', domain, 'A')
        logger.info('    %s', await query(resolver, domain, 'A'))
    logger.info('%s %s:', 'example.com', 'MX')
    logger.info('    %s', await query(resolver, 'example.com', 'MX'))


if __name__ == '__main__':
    sleep(2)
    logger.info('/etc/hosts:\n%s', Path('/etc/hosts').read_text())
    logger.info('/etc/resolv.conf:\n%s', Path('/etc/resolv.conf').read_text())
    logger.info('starting dns tests')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))

