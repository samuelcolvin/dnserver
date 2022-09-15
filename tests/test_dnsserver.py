from pathlib import Path
from typing import Any, Callable, Dict, List

import pytest
from dirty_equals import IsIP, IsPositive
from dns.resolver import Resolver as RawResolver

from dnserver import DNSServer

Resolver = Callable[[str, str], List[Dict[str, Any]]]


def convert_answer(answer) -> Dict[str, Any]:
    rdtype = answer.rdtype.name
    d = {'type': rdtype}
    if rdtype == 'MX':
        d.update(
            preference=answer.preference,
            value=answer.exchange.to_text(),
        )
    elif rdtype == 'SOA':
        d.update(
            rname=str(answer.rname.choose_relativity()),
            mname=str(answer.mname.choose_relativity()),
            serial=answer.serial,
            refresh=answer.refresh,
            retry=answer.retry,
            expire=answer.expire,
            minimum=answer.minimum,
        )
    else:
        d['value'] = answer.to_text()
    return d


@pytest.fixture(scope='session')
def dns_resolver():
    port = 5053
    zones_text = Path('example_zones.txt').read_text()

    server = DNSServer(zones_text, port=port)
    server.start()

    assert server.is_running

    resolver = RawResolver()
    resolver.nameservers = ['127.0.0.1']
    resolver.port = port

    def resolve(name: str, type_: str) -> List[Dict[str, Any]]:
        answers = resolver.resolve(name, type_)
        return [convert_answer(answer) for answer in answers]

    yield resolve

    server.stop()


def test_a_record(dns_resolver: Resolver):
    assert dns_resolver('example.com', 'A') == [
        {
            'type': 'A',
            'value': '1.2.3.4',
        },
    ]


def test_cname_record(dns_resolver: Resolver):
    assert dns_resolver('example.com', 'CNAME') == [
        {
            'type': 'CNAME',
            'value': 'whatever.com.',
        },
    ]


def test_mx_record(dns_resolver: Resolver):
    assert dns_resolver('example.com', 'MX') == [
        {
            'type': 'MX',
            'preference': 5,
            'value': 'whatever.com.',
        },
        {
            'type': 'MX',
            'preference': 10,
            'value': 'mx2.whatever.com.',
        },
        {
            'type': 'MX',
            'preference': 20,
            'value': 'mx3.whatever.com.',
        },
    ]


def test_proxy(dns_resolver: Resolver):
    assert dns_resolver('example.org', 'A') == [
        {
            'type': 'A',
            'value': IsIP(version=4),
        },
    ]


def test_soa(dns_resolver: Resolver):
    assert dns_resolver('example.com', 'SOA') == [
        {
            'type': 'SOA',
            'rname': 'dns.example.com.',
            'mname': 'ns1.example.com.',
            'serial': IsPositive(),
            'refresh': 3600,
            'retry': 10800,
            'expire': 86400,
            'minimum': 3600,
        }
    ]
