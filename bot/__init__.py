"""Bot client and event handlers."""

from .client import EMCBot
from .events import setup_events

__all__ = ['EMCBot', 'setup_events']