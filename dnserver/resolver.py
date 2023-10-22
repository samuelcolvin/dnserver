import typing as _ty

import dnslib as _dns
from dnslib.server import BaseResolver, DNSHandler, DNSRecord
from dnslib.proxy import ProxyResolver

from . import common as _common
from . import dnssec

R = _ty.TypeVar('R', bound=BaseResolver)
_TR = _ty.TypeVarTuple('_TR')


class RecordsResolver(BaseResolver):
    def __init__(self, records: _common.SharedObject[_common.Records] | _common.Records):
        self.records: _common.SharedObject[_common.Records] = records
        if not isinstance(records, _common.SharedObject):
            self.records = _common.SharedObject(self.records)

    def resolve(self, request: DNSRecord, handler: DNSHandler):
        with self.records as records:
            type_name = _dns.QTYPE[request.q.qtype]
            reply = request.reply()
            for record in records:
                if record.match(request.q):
                    reply.add_answer(record.rr)

            if reply.rr:
                _common.LOGGER.info('found zone for %s[%s], %d replies', request.q.qname, type_name, len(reply.rr))
                return reply

            # no direct zone so look for an SOA record for a higher level zone
            for record in records:
                if record.sub_match(request.q):
                    reply.add_answer(record.rr)

            if reply.rr:
                _common.LOGGER.info('found higher level SOA resource for %s[%s]', request.q.qname, type_name)
                return reply

            _common.LOGGER.info('no local zone found %s[%s]', request.q.qname, type_name)
            return request.reply()


class ProxyResolver(ProxyResolver):
    DEFAULT_TIMEOUT = 5
    DEFAULT_STRIP_AAA = False

    _KWARGS_MAP = ['port', 'timeout', 'strip_aaa', 'dns_sec']

    def __init__(self, address: str, port=None, timeout=None, strip_aaa=None, dns_sec=None):
        parts = address.strip().split(':')
        address = parts[0]
        kwargs = {}
        _stop_args = False
        for idx, val in enumerate(parts[1:]):
            if '=' in val:
                key, val = val.split('=')
                _stop_args = True
            elif _stop_args:
                raise ValueError(address)
            else:
                key = self._KWARGS_MAP[idx]
            kwargs[key] = val

        port = kwargs.get('port') if port is None else port
        timeout = kwargs.get('timeout') if timeout is None else timeout
        strip_aaa = kwargs.get('stip_aaa') if strip_aaa is None else strip_aaa
        dns_sec = kwargs.get('dns_sec') if dns_sec is None else dns_sec

        port = _common.DEFAULT_PORT if port is None else port
        timeout = self.DEFAULT_TIMEOUT if timeout is None else timeout
        strip_aaa = self.DEFAULT_STRIP_AAA if strip_aaa is None else strip_aaa
        self.dns_sec: _common.SharedObject[dict[str]] = False if dns_sec is None else dns_sec
        if (
            not self.dns_sec
            or isinstance(self.dns_sec, str)
            and self.dns_sec.strip().lower()
            in [
                'no',
                'false',
                '0',
                'disable',
                'disabled',
            ]
        ):
            self.dns_sec = False

        if self.dns_sec:
            if not isinstance(self.dns_sec, _common.SharedObject):
                self.dns_sec = _common.SharedObject(dns_sec)
            _replace = None
            with self.dns_sec as dns_sec:
                if not isinstance(dns_sec, _ty.Mapping):
                    if not dns_sec:
                        _replace = {}
                    else:
                        _replace = {'anchors': {}, 'verified': {}}
            if _replace is not None:
                self.dns_sec.set(_replace)

            with self.dns_sec as dns_sec:
                if not dns_sec.get('anchors'):
                    dns_sec['anchors'] = dnssec.TRUSTED_ANCHORS
                if dns_sec.get('verified') is None:
                    dns_sec['verified'] = {}

        super().__init__(address=address, port=int(port), timeout=int(timeout), strip_aaaa=bool(strip_aaa))

    def resolve(self, request: DNSRecord, handler: DNSHandler):
        type_name = _dns.QTYPE[request.q.qtype]
        _common.LOGGER.info('proxying %s[%s]', request.q.qname, type_name)
        if self.dns_sec:
            request.add_ar(_dns.EDNS0(flags="do", udp_len=4096))
        result = super().resolve(request, handler)
        if self.dns_sec:
            with self.dns_sec as dns_sec:
                try:
                    _common.LOGGER.info(f"Verifying DNSSEC for {request.q.qname}")
                    dnssec.verify(bytes(result.pack()), self.address, dns_sec['verified'], dns_sec['anchors'])
                    _common.LOGGER.info(f"Verified DNSSEC for {request.q.qname}")

                except Exception as e:
                    _common.LOGGER.warning(f"Could not verify DNSSEC for {request.q.qname}")
                    # More check see if ti was due to non existent or bad signature and take approiate action
        return result


class RoundRobinResolver(BaseResolver, _ty.Generic[*_TR]):
    def __init__(self, resolvers: tuple[*_TR]):
        self.resolvers = tuple(resolvers)

    def _resolvers(self, request: DNSRecord, handler: DNSHandler) -> _ty.Iterable[BaseResolver]:
        '''Gives the option to modify the order of resolvers or exclude resolver by request'''
        return self.resolvers

    def validate(self, answer: DNSRecord, resolver: BaseResolver, request: DNSRecord, handler: DNSHandler):
        '''Gives the option to decide if a request is valid or check the next resolver for a request'''
        return bool(answer and answer.header.rcode == 0 and answer.rr)

    def default_answer(self, badanswers: list[DNSRecord | None], request: DNSRecord, handler: DNSHandler):
        '''Override default response'''
        return badanswers[-1] if badanswers else request.reply()

    def resolve(self, request: DNSRecord, handler: DNSHandler):
        resolver: BaseResolver
        badanswers = []
        for resolver in self._resolvers(request, handler):
            answer: DNSRecord = resolver.resolve(request, handler)
            if self.validate(answer, resolver, request, handler):
                return answer
            else:
                badanswers.append(answer)
        return self.default_answer(badanswers, request, handler)


class ForwarderResolver(RoundRobinResolver[ProxyResolver]):
    resolvers: _ty.Tuple[ProxyResolver, ...]

    def __init__(self, upstream: str | _ty.List[str]):
        if isinstance(upstream, str):
            upstream = upstream.split(',')
        resolvers = [ProxyResolver(upstream) for upstream in upstream]
        super().__init__(resolvers)
