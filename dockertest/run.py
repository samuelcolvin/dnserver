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


async def query(resolver, domain, qtype):
    logger.info('%s %s:', domain, qtype)
    try:
        ans = await resolver.query(domain, qtype)
    except DNSError as e:
        logger.info('    %s: %s', e.__class__.__name__, e)
    else:
        for v in ans:
            logger.info('    %s', v)


async def main(loop):
    resolver = aiodns.DNSResolver(loop=loop)
    for domain in ('example.com', 'google.com', 'ns', 'test', 'fails'):
        await query(resolver, domain, 'A')
    await query(resolver, 'example.com', 'MX')
    await query(resolver, 'foobar.example.com', 'A')
    await query(resolver, 'testing.com', 'TXT')


if __name__ == '__main__':
    sleep(1)
    logger.info('/etc/hosts:\n%s', Path('/etc/hosts').read_text())
    logger.info('/etc/resolv.conf:\n%s', Path('/etc/resolv.conf').read_text())
    logger.info('starting dns tests')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))

