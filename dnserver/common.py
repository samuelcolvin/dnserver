from dnslib import dns, QTYPE
import dnslib as _dns
import logging as _log
import typing as _ty
from threading import Lock as _Lock
import datetime as _dt
from textwrap import wrap as _wrap
import dataclasses as _data
import re  as _re

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

RecordType = Literal[
    'A', 'AAAA', 'CAA', 'CNAME', 'DNSKEY', 'MX', 'NAPTR', 'NS', 'PTR', 'RRSIG', 'SOA', 'SRV', 'TXT', 'SPF'
]
RECORD_TYPES = RecordType.__args__  # type: ignore


LOGGER = _log.getLogger(__name__)
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
SERIAL_NO = int((_dt.datetime.utcnow() - _dt.datetime(1970, 1, 1)).total_seconds())

T = _ty.TypeVar('T')


class SharedObject(_ty.Generic[T]):
    def __init__(self, obj: T, lock: _Lock = None) -> None:
        self._obj = obj
        self.lock = lock or _Lock()

    def __enter__(self):
        self.lock.acquire()
        return self._obj

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()

    def set(self, obj: T):
        with self:
            self._obj = obj


@_data.dataclass
class Zone:
    host: str
    type: RecordType
    answer: str | list[str | int]
    # TODO we could add ttl and other args here if someone wanted it

    @classmethod
    def from_raw(cls, index: int, data: _ty.Any) -> 'Zone':
        if not isinstance(data, dict) or data.keys() != {'host', 'type', 'answer'}:
            raise ValueError(
                f'Zone {index} is not a valid dict, must have keys "host", "type" and "answer", got {data!r}'
            )

        host = data['host']
        if not isinstance(host, str):
            raise ValueError(f'Zone {index} is invalid, "host" must be string, got {data!r}')

        type_ = data['type']
        if type_ not in RECORD_TYPES:
            raise ValueError(f'Zone {index} is invalid, "type" must be one of {", ".join(RECORD_TYPES)}, got {data!r}')

        answer = data['answer']
        if isinstance(answer, str):
            answer = _re.sub(r'\s*\r?\n', '', answer)
        elif not isinstance(answer, list) or not all(isinstance(x, (str, int)) for x in answer):
            raise ValueError(
                f'Zone {index} is invalid, "answer" must be a string or list of strings and ints, got {data!r}'
            )

        return cls(host, type_, answer)


class Record:
    def __init__(self, zone: Zone):
        self._rname = _dns.DNSLabel(zone.host)

        rd_cls, self._rtype = TYPE_LOOKUP[zone.type]

        args: list[_ty.Any]
        if isinstance(zone.answer, str):
            if self._rtype == QTYPE.TXT:
                args = [_wrap(zone.answer, 255)]
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

        self.rr = _dns.RR(
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
