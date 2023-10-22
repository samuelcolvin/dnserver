import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, List, Callable, OrderedDict, TypeAlias
from .common import Zone, Record, Records, _Self


__all__ = 'Config'

Parser = Callable[[BinaryIO], dict]


def _yaml():
    import yaml

    return yaml.safe_load


def _json():
    import json

    return json.load


def _toml():
    if sys.version_info >= (3, 11):
        import tomllib as toml_
    else:
        import tomli as toml_
    return toml_.load


PARSERS: OrderedDict[str, Callable[[], Parser]] = OrderedDict((p.__name__.strip('_'), p) for p in [_toml, _yaml, _json])


def _all_parser(file: BinaryIO):
    for parser in PARSERS.values():
        try:
            return parser()(file)
        except:
            pass
    raise Exception()


@dataclass
class Config:
    zones: List[Zone]

    @classmethod
    def load(cls, zones_file: str | Path, format: str = None) -> _Self:
        file = Path(zones_file)
        data = None
        if not format:
            parser = _all_parser
        elif isinstance(format, str):
            parser = PARSERS[format]()
        else:
            parser = format

        with file.open('rb') as file:
            data = parser(file)
        try:
            zones = data['zones']
        except KeyError:
            raise ValueError(f'No zones found in {zones_file}')

        if not isinstance(zones, list):
            raise ValueError(f'Zones must be a list, not {type(zones).__name__}')

        return cls(zones=[Zone.from_raw(i, zone) for i, zone in enumerate(zones, start=1)])

    def records(self) -> Records:
        return [Record(zone) for zone in self.zones]
