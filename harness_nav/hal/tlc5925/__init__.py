"""TLC5925 16-channel constant-current LED sink driver HAL."""

from .tlc5925_driver import TLC5925Driver, MockTLC5925Driver

__all__ = ['TLC5925Driver', 'MockTLC5925Driver']
