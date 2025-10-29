"""Discord bot cogs."""

from .verification import VerificationCog
from .admin import AdminCog
from .auto_verify import AutoVerifyCog
from .scanner import ScannerCog

__all__ = ['VerificationCog', 'AdminCog', 'AutoVerifyCog', 'ScannerCog']