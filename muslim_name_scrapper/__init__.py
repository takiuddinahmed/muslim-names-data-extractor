"""
Muslim Names Scraper Package
A robust scraper for extracting Muslim names from muslimnames.com
"""

from .scraper import MuslimNamesScraper
from .network import NetworkManager
from .parser import HTMLParser
from .storage import DataStorage
from .progress import ProgressTracker
from .config import Config, get_config, reload_config

# Kaggle uploader is optional (requires kaggle package)
try:
    from .kaggle_uploader import KaggleUploader
    _has_kaggle = True
except ImportError:
    _has_kaggle = False

__version__ = "2.0.0"
__author__ = "Md Takiuddin"
__email__ = "contact@takiuddin.me"

__all__ = [
    'MuslimNamesScraper',
    'NetworkManager', 
    'HTMLParser',
    'DataStorage',
    'ProgressTracker',
    'Config',
    'get_config',
    'reload_config'
]

# Add KaggleUploader to exports if available
if _has_kaggle:
    __all__.append('KaggleUploader')
