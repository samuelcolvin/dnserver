from pathlib import Path

import pytest
from dns.resolver import Resolver

from dnserver import DNSServer


@pytest.fixture
def dns_resolver():
    port = 5053
    zone = Path('example_zones.txt').read_text()

    server = DNSServer(port, zone)
    server.start()

    resolver = Resolver()
    resolver.nameservers = ['127.0.0.1']
    resolver.port = port

    yield resolver

    server.stop()


def test_dnserver(dns_resolver):
    answers = dns_resolver.resolve('example.com', 'A')
    assert answers[0].address == '1.2.3.4'
