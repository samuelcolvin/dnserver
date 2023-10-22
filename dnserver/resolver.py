import typing as _ty

import dnslib as _dns
from dnslib.server import BaseResolver, DNSHandler, DNSRecord
from dnslib.proxy import ProxyResolver

from .common import LOGGER, DEFAULT_PORT, SharedObject, Record, Records

R = _ty.TypeVar('R', bound=BaseResolver)
_TR = _ty.TypeVarTuple('_TR')


class RecordsResolver(BaseResolver):
    def __init__(self, records: SharedObject[Records] | Records):
        self.records = records
        if not isinstance(records, SharedObject):
            self.records = SharedObject(self.records)

    def resolve(self, request: DNSRecord, handler: DNSHandler):
        with self.records as records:
            type_name = _dns.QTYPE[request.q.qtype]
            reply = request.reply()
            for record in records:
                if record.match(request.q):
                    reply.add_answer(record.rr)

            if reply.rr:
                LOGGER.info('found zone for %s[%s], %d replies', request.q.qname, type_name, len(reply.rr))
                return reply

            # no direct zone so look for an SOA record for a higher level zone
            for record in records:
                if record.sub_match(request.q):
                    reply.add_answer(record.rr)

            if reply.rr:
                LOGGER.info('found higher level SOA resource for %s[%s]', request.q.qname, type_name)
                return reply

            LOGGER.info('no local zone found %s[%s]', request.q.qname, type_name)
            return request.reply()


class ProxyResolver(ProxyResolver):
    DEFAULT_TIMEOUT = 5
    DEFAULT_STRIP_AAA = False

    def __init__(self, address: str, port=None, timeout=None, strip_aaa=None):
        parts = address.split(':') + [None] * 3
        address = parts[0]
        port = parts[1] if port is None else port
        timeout = parts[2] if timeout is None else timeout
        strip_aaa = parts[3] if strip_aaa is None else strip_aaa

        port = DEFAULT_PORT if port is None else port
        timeout = self.DEFAULT_TIMEOUT if timeout is None else timeout
        strip_aaa = self.DEFAULT_STRIP_AAA if strip_aaa is None else strip_aaa

        super().__init__(address=address, port=int(port), timeout=int(timeout), strip_aaaa=bool(strip_aaa))

    def resolve(self, request: DNSRecord, handler: DNSHandler):
        type_name = _dns.QTYPE[request.q.qtype]
        LOGGER.info('proxying %s[%s]', request.q.qname, type_name)
        return super().resolve(request, handler)


class RoundRobinResolver(BaseResolver, _ty.Generic[*_TR]):
    def __init__(self, resolvers: tuple[*_TR]):
        self.resolvers = tuple(resolvers)

    def resolve(self, request: DNSRecord, handler: DNSHandler):
        answer = request.reply()
        resolver: BaseResolver
        for resolver in self.resolvers:
            answer: DNSRecord = resolver.resolve(request, handler)
            if answer.header.rcode == 0 and answer.rr:
                return answer
        return answer


class ForwarderResolver(RoundRobinResolver):
    def __init__(self, upstream: str | _ty.List[str]):
        if isinstance(upstream, str):
            upstream = upstream.split(',')
        resolvers = [ProxyResolver(upstream) for upstream in upstream]
        super().__init__(resolvers)
