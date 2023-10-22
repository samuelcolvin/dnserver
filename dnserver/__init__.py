from .config import Config
from .common import *
from .main import DNSServer
from .version import VERSION

__all__ = 'DNSServer', 'Zone', '__version__'
__version__ = VERSION
