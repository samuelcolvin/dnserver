from __future__ import annotations as _annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

__all__ = 'load_records', 'RecordType', 'Zone'

RecordType = Literal[
    'A', 'AAAA', 'CAA', 'CNAME', 'DNSKEY', 'MX', 'NAPTR', 'NS', 'PTR', 'RRSIG', 'SOA', 'SRV', 'TXT', 'SPF'
]
RECORD_TYPES = RecordType.__args__  # type: ignore


@dataclass
class Zone:
    host: str
    type: RecordType
    answer: str | list[str | int]
    # TODO we could add ttl and other args here if someone wanted it

    @classmethod
    def from_raw(cls, index: int, data: Any) -> Zone:
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
            answer = re.sub(r'\s*\r?\n', '', answer)
        elif not isinstance(answer, list) or not all(isinstance(x, (str, int)) for x in answer):
            raise ValueError(
                f'Zone {index} is invalid, "answer" must be a string or list of strings and ints, got {data!r}'
            )

        return cls(host, type_, answer)


@dataclass
class Records:
    zones: list[Zone]


def load_records(zones_file: str | Path) -> Records:
    data = parse_toml(zones_file)
    try:
        zones = data['zones']
    except KeyError:
        raise ValueError(f'No zones found in {zones_file}')

    if not isinstance(zones, list):
        raise ValueError(f'Zones must be a list, not {type(zones).__name__}')
    return Records([Zone.from_raw(i, zone) for i, zone in enumerate(zones, start=1)])


def parse_toml(zones_file: str | Path) -> dict[str, Any]:
    if sys.version_info >= (3, 11):
        import tomllib as toml_
    else:
        import tomli as toml_

    with open(zones_file, 'rb') as rf:
        return toml_.load(rf)
