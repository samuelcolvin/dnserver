from __future__ import annotations as _annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from .common import Zone

__all__ = 'Records'

@dataclass
class Records:
    zones: list[Zone]

    @classmethod
    def load(cls, zones_file: str | Path) -> Records:
        data = _parse_toml(zones_file)
        try:
            zones = data['zones']
        except KeyError:
            raise ValueError(f'No zones found in {zones_file}')

        if not isinstance(zones, list):
            raise ValueError(f'Zones must be a list, not {type(zones).__name__}')
        return cls([Zone.from_raw(i, zone) for i, zone in enumerate(zones, start=1)])


def _parse_toml(zones_file: str | Path) -> dict[str, Any]:
    if sys.version_info >= (3, 11):
        import tomllib as toml_
    else:
        import tomli as toml_

    with open(zones_file, 'rb') as rf:
        return toml_.load(rf)
