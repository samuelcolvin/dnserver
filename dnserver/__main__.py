"""
This allows usage via `python -m dnserver`
"""
import logging

from .cli import cli
from .common import LOGGER

if __name__ == '__main__':
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%H:%M:%S'))

    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    cli()
