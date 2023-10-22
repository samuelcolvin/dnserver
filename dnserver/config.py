import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List
from .common import Zone, Record, Records, _Self

__all__ = 'Config'


@dataclass
class Config:
    zones: List[Zone]

    @classmethod
    def load(cls, zones_file: str | Path) -> _Self:
        data = _parse_toml(zones_file)
        try:
            zones = data['zones']
        except KeyError:
            raise ValueError(f'No zones found in {zones_file}')

        if not isinstance(zones, list):
            raise ValueError(f'Zones must be a list, not {type(zones).__name__}')
        return cls(zones=[Zone.from_raw(i, zone) for i, zone in enumerate(zones, start=1)])

    def records(self) -> Records:
        return [Record(zone) for zone in self.zones]


def _parse_toml(zones_file: str | Path) -> dict[str, Any]:
    if sys.version_info >= (3, 11):
        import tomllib as toml_
    else:
        import tomli as toml_

    with open(zones_file, 'rb') as rf:
        return toml_.load(rf)
