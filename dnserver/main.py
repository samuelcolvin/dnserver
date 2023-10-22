from __future__ import annotations as _annotations

import logging
from pathlib import Path
from types import NoneType
from typing import Any, List, Generic, overload, Iterable, TypeAlias, Sequence

from dnslib.server import BaseResolver as LibBaseResolver, DNSServer as LibDNSServer

from .config import Config
from .resolver import BaseResolver, RecordsResolver, ForwarderResolver, RoundRobinResolver, R, Records
from .common import LOGGER, DEFAULT_PORT, SharedObject, Record, Zone, _Self, DEFAULT

__all__ = 'SimpleDNSServer', 'DNSServer'

DEFAULT_UPSTREAM = '1.1.1.1'
Port: TypeAlias = tuple[int, bool]


def _ports(obj):
    if isinstance(obj, Sequence):
        if len(obj) == 2 and isinstance(obj[1], (bool, NoneType)):
            return (obj[0], obj[1])
        return None
    return (obj, None)


class DNSServer(Generic[R]):
    resolver: R

    @overload
    def __new__(self, resolver: R, port: int | Port | Iterable[int | Port] | None = None) -> _Self[R]:
        ...

    @overload
    def __new__(self, resolver: str, port: int | Port | Iterable[int | Port] | None = None) -> _Self[ForwarderResolver]:
        ...

    @overload
    def __new__(
        self,
        resolver: Records | SharedObject[Records] | None = None,
        port: int | Port | Iterable[int | Port] | None = None,
    ) -> _Self[RecordsResolver]:
        ...

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        resolver: R | Records | SharedObject[Records] | str | None = None,
        port: int | Port | Iterable[int | Port] | None = None,
    ):
        ports: list[Port] = DEFAULT_PORT if port is None else port
        _port = _ports(ports)
        if _port is not None:
            ports = [_port]
        self.servers: dict[Port, LibDNSServer | None] = {}
        for port in ports:
            port, tcp = _ports(port)
            port = int(port or DEFAULT_PORT)
            if tcp is None or tcp is False:
                self.servers[(port, False)] = None
            if tcp is None or tcp is True:
                self.servers[(port, True)] = None

        self.resolver = resolver or list([])
        if isinstance(self.resolver, list):
            self.resolver = SharedObject(self.resolver)
        if isinstance(self.resolver, SharedObject):
            self.resolver = RecordsResolver(self.resolver)
        if isinstance(self.resolver, str):
            self.resolver = ForwarderResolver(self.resolver)
        if not isinstance(self.resolver, LibBaseResolver):
            raise ValueError(self.resolver)

    def start(self):
        for port, tcp in self.servers:
            LOGGER.info('starting DNS server on port %d protocol: %s', port, 'tcp' if tcp else 'udp')
            server = LibDNSServer(self.resolver, port=port, tcp=tcp)
            server.start_thread()
            self.servers[(port, tcp)] = server

    def stop(self):
        for server in self.servers.values():
            server.stop()
            server.server.server_close()

    @property
    def is_running(self):
        for server in self.servers.values():
            if server.isAlive():
                return True
        return False

    @property
    def port(self):
        return next(iter(self.servers.keys()))[0]


class SimpleDNSServer(DNSServer[RoundRobinResolver[RecordsResolver, ForwarderResolver] | RecordsResolver]):
    def __new__(cls, *args, **kwargs) -> 'SimpleDNSServer':
        return super().__new__(cls)

    def __init__(
        self,
        records: Records | SharedObject[Records] | None = None,
        port: int | Port | Iterable[int | Port] | None = DEFAULT_PORT,
        upstream: str | List[str] | None = DEFAULT_UPSTREAM,
    ):
        super().__init__(records, port)
        self.records: SharedObject[Records] = self.resolver.records
        if upstream:
            LOGGER.info('upstream DNS server "%s"', upstream)
            self.resolver = RoundRobinResolver([self.resolver, ForwarderResolver(upstream)])
        else:
            LOGGER.info('without upstream DNS server')

    @classmethod
    def from_config(
        cls,
        config: str | Path | Config,
        *,
        port: int | str | None = None,
        upstream: str | None = DEFAULT,
    ) -> 'SimpleDNSServer':
        if isinstance(config, (str, Path)):
            config = Config.load(config)
        if port is None:
            port = config.port or DEFAULT_PORT
        if upstream is DEFAULT:
            upstream = config.upstream or DEFAULT_UPSTREAM
        records = config.records()
        LOGGER.info(
            'loaded %d zone record from %s, with %s as a proxy DNS server',
            len(config.zones),
            config,
            upstream,
        )
        return SimpleDNSServer(records, port=port, upstream=upstream)

    def add_record(self, record: Zone | Record):
        if not isinstance(record, Record):
            record = Record(record)
        with self.records as records:
            records.append(record)

    def set_records(self, records: Sequence[Zone | Record]):
        _records = []
        for record in records:
            if not isinstance(record, Record):
                record = Record(record)
            _records.append(record)
        self.records.set(_records)
