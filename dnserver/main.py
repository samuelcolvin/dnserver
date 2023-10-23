from enum import Flag, auto
from pathlib import Path
from typing import Generic, Iterable, NamedTuple, Union, overload
from urllib.parse import urlparse

from dnslib.server import DNSServer as LibDNSServer

from .common import DEFAULT, DEFAULT_PORT, LOGGER, Record, Records, SharedObject, Zone, _Self
from .config import Config
from .resolver import BaseResolver, ForwarderResolver, R, RecordsResolver, RoundRobinResolver

__all__ = 'SimpleDNSServer', 'DNSServer'

extras_args = {}

try:
    from enum import STRICT

    extras_args['boundary'] = STRICT
except ImportError:
    pass


class IPProto(Flag, **extras_args):
    UDP = auto()
    TCP = auto()
    BOTH = TCP | UDP


class IPBind(NamedTuple):
    address: str
    port: 'int | None'
    proto: IPProto

    def expand(self):
        for proto in IPProto:
            if proto in self.proto:
                yield IPBind(*self[:2], proto)

    @classmethod
    def parse(
        cls,
        address: str,
        port: 'str | int' = None,
        proto: 'str | IPProto' = None,
        *,
        default_port=0,
        default_address='',
        default_proto=IPProto.BOTH,
    ):
        if not address:
            address = ''
        try:
            _port = int(address)
            address = f'{default_address}:{_port}'
        except Exception:
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


IPBindLike = Union[int, str, IPBind, tuple]


class DNSServer(Generic[R]):
    resolver: R

    @overload
    def __new__(self, resolver: R, port: 'IPBindLike | Iterable[IPBindLike] | None' = None) -> 'DNSServer[R]':
        ...

    @overload
    def __new__(
        self, resolver: str, port: 'IPBindLike | Iterable[IPBindLike] | None' = None
    ) -> 'DNSServer[ForwarderResolver]':
        ...

    @overload
    def __new__(
        self,
        resolver: 'Records | SharedObject[Records] | None' = None,
        port: 'IPBindLike | Iterable[IPBindLike] | None' = None,
    ) -> 'DNSServer[RecordsResolver]':
        ...

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        resolver: 'R | Records | SharedObject[Records] | str | None' = None,
        port: 'int | str | IPBind | Iterable[int | str | IPBind] | None' = None,
    ):
        ports: 'list[IPBind]' = DEFAULT_PORT if port is None else port
        if not isinstance(ports, list):
            ports = [ports]
        self.servers: 'dict[IPBind, LibDNSServer | None]' = {}
        for port in ports:
            if not isinstance(port, tuple):
                port = (port,)
            bind = IPBind.parse(*port, default_port=DEFAULT_PORT)
            for _bind in bind.expand():
                self.servers[_bind] = None

        self.resolver = resolver or list([])
        if isinstance(self.resolver, list):
            self.resolver = SharedObject(self.resolver)
        if isinstance(self.resolver, SharedObject):
            self.resolver = RecordsResolver(self.resolver)
        if isinstance(self.resolver, str):
            self.resolver = ForwarderResolver(self.resolver)
        if not isinstance(self.resolver, BaseResolver):
            raise ValueError(self.resolver)

    def start(self, raise_=False):
        for bind in self.servers:
            LOGGER.info('starting DNS server on ip: %s port: %d protocol: %s', *bind)
            try:
                server = LibDNSServer(
                    self.resolver, address=bind.address, port=bind.port, tcp=bind.proto is IPProto.TCP
                )
                server.start_thread()
                self.servers[bind] = server
            except OSError as e:
                LOGGER.error(f'Could not start server on: {bind} due to: {e}')

    def stop(self):
        for server in self.servers.values():
            if server:
                server.stop()
                server.server.server_close()

    @property
    def is_running(self):
        for server in self.servers.values():
            if server and server.isAlive():
                return True
        return False

    @property
    def port(self):
        return next(( bind for bind, server in self.servers.items() if server and server.isAlive())).port


class SimpleDNSServer(DNSServer[Union[RoundRobinResolver[RecordsResolver, ForwarderResolver], RecordsResolver]]):
    DEFAULT_UPSTREAM = '1.1.1.1'

    def __new__(cls, *args, **kwargs) -> '_Self':
        return super().__new__(cls)

    def __init__(
        self,
        records: 'Records | SharedObject[Records] | None' = None,
        port: 'IPBindLike | Iterable[IPBindLike] | None' = DEFAULT_PORT,
        upstream: 'str | list[str] | None' = DEFAULT_UPSTREAM,
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
        config: 'str | Path | Config',
        *,
        port: 'IPBindLike | None' = None,
        upstream: 'str | None' = DEFAULT,
    ) -> '_Self':
        if isinstance(config, (str, Path)):
            config = Config.load(config)
        if port is None:
            port = config.port or DEFAULT_PORT
        if upstream is DEFAULT:
            upstream = config.upstream or cls.DEFAULT_UPSTREAM
        records = config.records()
        LOGGER.info(
            'loaded %d zone record from %s, with %s as a proxy DNS server',
            len(config.zones),
            config,
            upstream,
        )
        return cls(records, port=port, upstream=upstream)

    def add_record(self, record: 'Zone | Record'):
        if not isinstance(record, Record):
            record = Record(record)
        with self.records as records:
            records.append(record)

    def set_records(self, records: 'Iterable[Zone | Record]'):
        _records = []
        for record in records:
            if not isinstance(record, Record):
                record = Record(record)
            _records.append(record)
        self.records.set(_records)
