from .load_records import Zone
from .main import DEFAULT_TTL, DEFAULT_TTL_NS_SOA, DNSServer
from .version import VERSION

__all__ = 'DNSServer', 'Zone', 'DEFAULT_TTL', 'DEFAULT_TTL_NS_SOA', '__version__'
__version__ = VERSION
