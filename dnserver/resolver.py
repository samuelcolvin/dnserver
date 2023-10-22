import typing as _ty

from dnslib.server import BaseResolver, DNSHandler, DNSRecord
from dnslib.proxy import ProxyResolver

from .common import LOGGER, DEFAULT_PORT, QTYPE, SharedObject, Record
from .load_records import Records

R = _ty.TypeVar('R', bound=BaseResolver)
_TR = _ty.TypeVarTuple('_TR')


class RecordsResolver(BaseResolver):
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
    def __init__(self, upstream: str, port=DEFAULT_PORT, timeout=5):
        super().__init__(address=upstream, port=int(port or DEFAULT_PORT), timeout=int(timeout or 5))

    def resolve(self, request: DNSRecord, handler: DNSHandler):
        type_name = QTYPE[request.q.qtype]
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
