from .config import Config
from .common import *
from .main import SimpleDNSServer
from .version import VERSION

__all__ = 'SimpleDNSServer', 'Zone', '__version__'
__version__ = VERSION
