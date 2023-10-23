import dataclasses as _data
import datetime as _dt
import logging as _log
import re as _re
import typing as _ty
from textwrap import wrap as _wrap
from threading import Lock as _Lock
from typing import Any as _Any

import dnslib as _dns
from dnslib import QTYPE as _QT

try:
    from typing import Literal as _Lit
except ImportError:
    from typing_extensions import Literal as _Lit
try:
    from typing import Self as _Self
except ImportError:
    from typing_extensions import Self as _Self


RecordType = _Lit[
    'A', 'AAAA', 'CAA', 'CNAME', 'DNSKEY', 'MX', 'NAPTR', 'NS', 'PTR', 'RRSIG', 'SOA', 'SRV', 'TXT', 'SPF'  # noqa: F821
]
RECORD_TYPES = RecordType.__args__  # type: ignore


LOGGER = _log.getLogger(__name__)
TYPE_LOOKUP = {
    'A': (_dns.A, _QT.A),
    'AAAA': (_dns.AAAA, _QT.AAAA),
    'CAA': (_dns.CAA, _QT.CAA),
    'CNAME': (_dns.CNAME, _QT.CNAME),
    'DNSKEY': (_dns.DNSKEY, _QT.DNSKEY),
    'MX': (_dns.MX, _QT.MX),
    'NAPTR': (_dns.NAPTR, _QT.NAPTR),
    'NS': (_dns.NS, _QT.NS),
    'PTR': (_dns.PTR, _QT.PTR),
    'RRSIG': (_dns.RRSIG, _QT.RRSIG),
    'SOA': (_dns.SOA, _QT.SOA),
    'SRV': (_dns.SRV, _QT.SRV),
    'TXT': (_dns.TXT, _QT.TXT),
    'SPF': (_dns.TXT, _QT.TXT),
}
DEFAULT_PORT = 53
SERIAL_NO = int((_dt.datetime.utcnow() - _dt.datetime(1970, 1, 1)).total_seconds())

T = _ty.TypeVar('T')


class _Default:
    ...

    def __bool__(self):
        return False


DEFAULT = _Default()


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
    answer: 'str | list[str | int]'
    # TODO we could add ttl and other args here if someone wanted it

    @classmethod
    def from_raw(cls, index: int, data: _ty.Any) -> '_Self':
        if not isinstance(data, dict) or data.keys() != {'host', 'type', 'answer'}:
            raise ValueError(
                f'Zone {index} is not a valid dict, must have keys "host", "type" and "answer", got {data!r}'
            )

        host = data['host']
        if not isinstance(host, str):
            raise ValueError(f'Zone {index} is invalid, "host" must be string, got {data!r}')

        type_ = data['type']
        if type_ not in RECORD_TYPES:
            raise ValueError(
                f'Zone {index} is invalid, "type" must be one of {", ".join(RECORD_TYPES)}, got {data!r}'  # noqa: Q000
            )

        answer = data['answer']
        if isinstance(answer, str):
            answer = _re.sub(r'\s*\r?\n', '', answer)
        elif not isinstance(answer, list) or not all(isinstance(x, (str, int)) for x in answer):
            raise ValueError(
                f'Zone {index} is invalid, "answer" must be a string or list of strings and ints, got {data!r}'
            )

        return cls(host, type_, answer)

    def rr(zone):
        rname = _dns.DNSLabel(zone.host)

        rd_cls, rtype = TYPE_LOOKUP[zone.type]
        args: list[_ty.Any]
        if isinstance(zone.answer, str):
            if rtype == _QT.TXT:
                args = [_wrap(zone.answer, 255)]
            else:
                args = [zone.answer]
        else:
            if rtype == _QT.SOA and len(zone.answer) == 2:
                # add sensible times to SOA
                args = zone.answer + [(SERIAL_NO, 3600, 3600 * 3, 3600 * 24, 3600)]
            else:
                args = zone.answer

        if rtype in (_QT.NS, _QT.SOA):
            ttl = 3600 * 24
        else:
            ttl = 300

        return _dns.RR(
            rname=rname,
            rtype=rtype,
            rdata=rd_cls(*args),
            ttl=ttl,
        )


class Record:
    def __init__(self, record: 'Zone | _dns.RR'):
        if isinstance(record, Zone):
            record = record.rr()
        self.rr = record

    def __getattr__(self, __name: str) -> _Any:
        return getattr(self.rr, __name)

    def match(self, q: _dns.DNSQuestion) -> bool:
        return q.qname == self.rr._rname and (q.qtype == _QT.ANY or q.qtype == self.rr.rtype)

    def sub_match(self, q: _dns.DNSQuestion) -> bool:
        return self.rr.rtype == _QT.SOA and q.qname.matchSuffix(self.rr.rname)


if _ty.TYPE_CHECKING:

    class Records(_ty.List[Record]):
        ...

else:

    class Records(list):
        ...
