from __future__ import annotations as _annotations

import logging
from pathlib import Path
from types import NoneType
from typing import Any, List, Generic, overload, Iterable, TypeAlias, Sequence, NamedTuple

from dnslib.server import DNSServer as LibDNSServer
from enum import Flag, auto, STRICT
from urllib.parse import urlparse

from .config import Config
from .resolver import BaseResolver, RecordsResolver, ForwarderResolver, RoundRobinResolver, R, Records
from .common import LOGGER, DEFAULT_PORT, SharedObject, Record, Zone, _Self, DEFAULT

__all__ = 'SimpleDNSServer', 'DNSServer'

DEFAULT_UPSTREAM = '1.1.1.1'
Port: TypeAlias = tuple[int, bool]


class IPProto(Flag, boundary=STRICT):
    UDP = auto()
    TCP = auto()
    BOTH = TCP | UDP


class IPBind(NamedTuple):
    address: str
    port: int | None
    proto: IPProto

    @classmethod
    def parse(
        cls,
        address: str,
        port: str | int = None,
        proto: str | IPProto = None,
        /,
        default_port=0,
        default_address='0.0.0.0',
        default_proto=IPProto.BOTH,
    ):
        if not address:
            address = ''
        try:
            _port = int(address)
            address = f'{default_address}:{_port}'
        except:
            pass
        address = str(address or default_address)
        if '://' not in address:
            address = 'none://' + address
        parsed = urlparse(address)
        address = parsed.hostname or default_address
        if port is None:
            port = parsed.port or default_port
        if proto is None and parsed.scheme != 'none':
            proto = parsed.scheme
        if proto is None:
            proto = default_proto
        if not isinstance(proto, IPProto):
            proto = proto.upper()
            if proto in IPProto:
                proto = IPProto[proto]
            else:
                raise ValueError(proto)
        return cls(address, int(port), proto)


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
        port: int | str | IPBind | List[int | str | IPBind] | None = None,
    ):
        ports: list[Port] = DEFAULT_PORT if port is None else port
        if not isinstance(ports, list):
            ports = [ports]
        self.servers: dict[IPBind, LibDNSServer | None] = {}
        for port in ports:
            if not isinstance(port, tuple):
                port = (port,)
            bind = IPBind.parse(*port, default_port=DEFAULT_PORT)
            for proto in bind.proto:
                self.servers[IPBind(bind.address, bind.port, proto)] = None

        self.resolver = resolver or list([])
        if isinstance(self.resolver, list):
            self.resolver = SharedObject(self.resolver)
        if isinstance(self.resolver, SharedObject):
            self.resolver = RecordsResolver(self.resolver)
        if isinstance(self.resolver, str):
            self.resolver = ForwarderResolver(self.resolver)
        if not isinstance(self.resolver, BaseResolver):
            raise ValueError(self.resolver)

    def start(self):
        for bind in self.servers:
            LOGGER.info('starting DNS server on ip: %s port: %d protocol: %s', *bind)
            server = LibDNSServer(self.resolver, address=bind.address, port=bind.port, tcp=bind.proto is IPProto.TCP)
            server.start_thread()
            self.servers[bind] = server

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
        return next(iter(self.servers.keys())).port


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
