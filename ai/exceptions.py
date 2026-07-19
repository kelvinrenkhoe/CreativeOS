"""Exceptions raised by the CreativeOS AI framework."""


class AIError(Exception):
    """Base exception for AI framework failures."""


class UnknownProviderError(AIError):
    """Raised when an AI provider is not registered."""


class ProviderConfigurationError(AIError):
    """Raised when an AI provider cannot be configured."""
