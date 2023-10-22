from __future__ import annotations as _annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from .common import Zone

__all__ = 'load_records', 'RecordType'

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
