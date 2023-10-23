from .common import LOGGER, Record, SharedObject, Zone
from .config import Config
from .main import DNSServer, SimpleDNSServer
from .resolver import BaseResolver, ForwarderResolver, ProxyResolver, RecordsResolver, RoundRobinResolver
from .version import VERSION

__all__ = (
    'SimpleDNSServer',
    'Zone',
    '__version__',
    'LOGGER',
    'Record',
    'SharedObject',
    'Config',
    'DNSServer',
    'BaseResolver',
    'ForwarderResolver',
    'ProxyResolver',
    'RecordsResolver',
    'RoundRobinResolver',
)
__version__ = VERSION
