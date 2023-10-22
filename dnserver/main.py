from __future__ import annotations as _annotations

import logging
from datetime import datetime
from pathlib import Path
from textwrap import wrap
from types import NoneType
from typing import Any, List, Generic, TypeVar, overload, TypeVarTuple, Iterable, TypeAlias, Sequence, Tuple
from threading import Lock

from dnslib import QTYPE, RR, DNSLabel, dns, DNSRecord
from dnslib.proxy import ProxyResolver as LibProxyResolver
from dnslib.server import BaseResolver as LibBaseResolver, DNSServer as LibDNSServer, DNSHandler

from .load_records import Records, Zone, load_records

__all__ = 'DNSServer', 'logger'

SERIAL_NO = int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds())

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%H:%M:%S'))

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

TYPE_LOOKUP = {
    'A': (dns.A, QTYPE.A),
    'AAAA': (dns.AAAA, QTYPE.AAAA),
    'CAA': (dns.CAA, QTYPE.CAA),
    'CNAME': (dns.CNAME, QTYPE.CNAME),
    'DNSKEY': (dns.DNSKEY, QTYPE.DNSKEY),
    'MX': (dns.MX, QTYPE.MX),
    'NAPTR': (dns.NAPTR, QTYPE.NAPTR),
    'NS': (dns.NS, QTYPE.NS),
    'PTR': (dns.PTR, QTYPE.PTR),
    'RRSIG': (dns.RRSIG, QTYPE.RRSIG),
    'SOA': (dns.SOA, QTYPE.SOA),
    'SRV': (dns.SRV, QTYPE.SRV),
    'TXT': (dns.TXT, QTYPE.TXT),
    'SPF': (dns.TXT, QTYPE.TXT),
}
DEFAULT_PORT = 53
DEFAULT_UPSTREAM = '1.1.1.1'


class Record:
    def __init__(self, zone: Zone):
        self._rname = DNSLabel(zone.host)

        rd_cls, self._rtype = TYPE_LOOKUP[zone.type]

        args: list[Any]
        if isinstance(zone.answer, str):
            if self._rtype == QTYPE.TXT:
                args = [wrap(zone.answer, 255)]
            else:
                args = [zone.answer]
        else:
            if self._rtype == QTYPE.SOA and len(zone.answer) == 2:
                # add sensible times to SOA
                args = zone.answer + [(SERIAL_NO, 3600, 3600 * 3, 3600 * 24, 3600)]
            else:
                args = zone.answer

        if self._rtype in (QTYPE.NS, QTYPE.SOA):
            ttl = 3600 * 24
        else:
            ttl = 300

        self.rr = RR(
            rname=self._rname,
            rtype=self._rtype,
            rdata=rd_cls(*args),
            ttl=ttl,
        )

    def match(self, q):
        return q.qname == self._rname and (q.qtype == QTYPE.ANY or q.qtype == self._rtype)

    def sub_match(self, q):
        return self._rtype == QTYPE.SOA and q.qname.matchSuffix(self._rname)

    def __str__(self):
        return str(self.rr)


T = TypeVar('T')


class SharedObject(Generic[T]):
    def __init__(self, obj: T, lock: Lock = None) -> None:
        self._obj = obj
        self.lock = lock or Lock()

    def __enter__(self):
        self.lock.acquire()
        return self._obj

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()

    def set(self, obj: T):
        with self:
            self._obj = obj


class RecordsResolver(LibBaseResolver):
    def __init__(self, records: SharedObject[Records]):
        self._records = records

    def records(self):
        with self._records as records:
            return [Record(zone) for zone in records.zones]

    def resolve(self, request: DNSRecord, handler: DNSHandler):
        records = self.records()
        type_name = QTYPE[request.q.qtype]
        reply = request.reply()
        for record in records:
            if record.match(request.q):
                reply.add_answer(record.rr)

        if reply.rr:
            logger.info('found zone for %s[%s], %d replies', request.q.qname, type_name, len(reply.rr))
            return reply

        # no direct zone so look for an SOA record for a higher level zone
        for record in records:
            if record.sub_match(request.q):
                reply.add_answer(record.rr)

        if reply.rr:
            logger.info('found higher level SOA resource for %s[%s]', request.q.qname, type_name)
            return reply

        logger.info('no local zone found %s[%s]', request.q.qname, type_name)
        return request.reply()


class ProxyResolver(LibProxyResolver):
    def __init__(self, upstream: str, port=DEFAULT_PORT, timeout=5):
        super().__init__(address=upstream, port=int(port or DEFAULT_PORT), timeout=int(timeout or 5))

    def resolve(self, request: DNSRecord, handler: DNSHandler):
        type_name = QTYPE[request.q.qtype]
        logger.info('proxying %s[%s]', request.q.qname, type_name)
        return super().resolve(request, handler)


R = TypeVar('R', bound=LibBaseResolver)
TR = TypeVarTuple('TR')


class RoundRobinResolver(LibBaseResolver, Generic[R]):
    def __init__(self, resolvers: Sequence[R]):
        self.resolvers = tuple(resolvers)

    def resolve(self, request: DNSRecord, handler: DNSHandler):
        answer = request.reply()
        resolver: LibBaseResolver
        for resolver in self.resolvers:
            answer: DNSRecord = resolver.resolve(request, handler)
            if answer.header.rcode == 0 and answer.rr:
                return answer
        return answer


Port: TypeAlias = tuple[int, bool]


def _ports(obj):
    if isinstance(obj, Sequence):
        if len(obj) == 2 and isinstance(obj[1], (bool, NoneType)):
            return (obj[0], obj[1])
        return None
    return (obj, None)


class BaseDNSServer(Generic[R]):
    resolver: R

    @overload
    def __new__(self, resolver: R, port: int | Port | Iterable[int | Port] | None = None) -> BaseDNSServer[R]:
        ...

    @overload
    def __new__(
        self, resolver: str, port: int | Port | Iterable[int | Port] | None = None
    ) -> BaseDNSServer[RoundRobinResolver | ProxyResolver]:
        ...

    @overload
    def __new__(
        self,
        resolver: Records | SharedObject[Records] | None = None,
        port: int | Port | Iterable[int | Port] | None = None,
    ) -> BaseDNSServer[RecordsResolver]:
        ...

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        resolver: R | Records | SharedObject[Records] | str | None = None,
        port: int | Port | Iterable[int | Port] | None = None,
    ):
        ports: list[Port] = DEFAULT_PORT if port is None else port
        _port = _ports(ports)
        if _port is not None:
            ports = [_port]
        self.servers: dict[Port, LibDNSServer | None] = {}
        for port in ports:
            port, tcp = _ports(port)
            port = int(port or DEFAULT_PORT)
            if tcp is None or tcp is False:
                self.servers[(port, False)] = None
            if tcp is None or tcp is True:
                self.servers[(port, True)] = None

        self.resolver = resolver or Records(zones=[])
        if isinstance(self.resolver, Records):
            self.resolver = SharedObject(self.resolver)
        if isinstance(self.resolver, SharedObject):
            self.resolver = RecordsResolver(self.resolver)
        if isinstance(self.resolver, str):
            resolvers = [ProxyResolver(*upstream.split(":")) for upstream in resolver.split(',')]
            if len(resolvers) > 1:
                self.resolver = RoundRobinResolver(resolvers)
            else:
                self.resolver = resolvers[0]

        if not isinstance(self.resolver, LibBaseResolver):
            raise ValueError(self.resolver)

    def start(self):
        for port, tcp in self.servers:
            logger.info('starting DNS server on port %d protocol: %s', port, 'tcp' if tcp else 'udp')
            server = LibDNSServer(self.resolver, port=port, tcp=tcp)
            server.start_thread()
            self.servers[(port, tcp)] = server

    def stop(self):
        for server in self.servers.values():
            server.stop()
            server.server.server_close()

    @property
    def is_running(self):
        for server in self.servers.values():
            if server.isAlive():
                return True
        return False

    @property
    def port(self):
        return next(self.servers.keys().__iter__())[0]


class DNSServer(BaseDNSServer[RoundRobinResolver[RecordsResolver, ProxyResolver] | RecordsResolver]):
    def __new__(cls, *args, **kwargs) -> 'DNSServer':
        return super().__new__(cls)

    def __init__(
        self,
        records: Records | SharedObject[Records] | None = None,
        port: int | Port | Iterable[int | Port] | None = DEFAULT_PORT,
        upstream: str | None = DEFAULT_UPSTREAM,
    ):
        super().__init__(records, port)
        self.records: SharedObject[Records] = self.resolver._records
        if upstream:
            logger.info('upstream DNS server "%s"', upstream)
            self.resolver = RoundRobinResolver(
                [self.resolver, *[ProxyResolver(*upstream.split(":")) for upstream in upstream.split(',')]]
            )
        else:
            logger.info('without upstream DNS server')

    @classmethod
    def from_toml(
        cls, zones_file: str | Path, *, port: int | str | None = DEFAULT_PORT, upstream: str | None = DEFAULT_UPSTREAM
    ) -> 'DNSServer':
        records = load_records(zones_file)
        logger.info(
            'loaded %d zone record from %s, with %s as a proxy DNS server',
            len(records.zones),
            zones_file,
            upstream,
        )
        return DNSServer(records, port=port, upstream=upstream)

    def add_record(self, zone: Zone):
        with self.records as records:
            records.zones.append(zone)

    def set_records(self, zones: List[Zone]):
        with self.records as records:
            records.zones = zones
