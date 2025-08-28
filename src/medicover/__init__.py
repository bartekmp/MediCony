"""
Medicover module - contains functionality for working with Medicover API.
This includes appointment search, booking, and watch functionality.
"""

from .appointment import Appointment
from .watch import Watch

__all__ = ["Appointment", "Watch"]
