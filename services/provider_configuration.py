"""Resolve provider configuration and credentials without exposing secret values."""

import os
from dataclasses import dataclass
from typing import Protocol

from services.provider_execution import ProviderExecutionAdapter


class ProviderConfigurationError(ValueError):
    """Reject unsafe or incomplete provider configuration."""


@dataclass(frozen=True, slots=True)
class ProviderOption:
    """One immutable, non-secret adapter configuration option."""

    name: str
    value: str


@dataclass(frozen=True, slots=True)
class ProviderConfiguration:
    """Non-secret configuration for one media execution provider."""

    provider: str
    credential_ref: str
    media_types: tuple[str, ...]
    model: str = ""
    endpoint: str = ""
    timeout_seconds: int = 60
    options: tuple[ProviderOption, ...] = ()


class SecretSource(Protocol):
    """Resolve an opaque credential reference at the execution boundary."""

    def resolve(self, reference: str) -> str:
        """Return a secret value without logging or persisting it."""
        ...


class ProviderAdapterFactory(Protocol):
    """Construct one adapter using validated configuration and a resolved secret."""

    @property
    def provider(self) -> str:
        """Return the provider handled by this factory."""
        ...

    def create(
        self,
        configuration: ProviderConfiguration,
        credential: str,
    ) -> ProviderExecutionAdapter:
        """Build an adapter without retaining the credential in domain state."""
        ...


class EnvironmentSecretSource:
    """Resolve credentials from named environment variables."""

    def resolve(self, reference: str) -> str:
        """Read one required environment variable by opaque reference."""
        value = os.environ.get(reference, "")
        if not value.strip():
            raise ProviderConfigurationError("provider credential is unavailable")
        return value


class ProviderConfigurationService:
    """Validate provider settings and construct a capability-safe adapter."""

    _MEDIA_TYPES = ("image", "video")

    def create_adapter(
        self,
        configuration: ProviderConfiguration,
        secret_source: SecretSource,
        factory: ProviderAdapterFactory,
    ) -> ProviderExecutionAdapter:
        """Resolve a secret only after validating all non-secret configuration."""
        normalized = self.validate(configuration)
        factory_provider = self._required(factory.provider, "factory provider").casefold()
        if factory_provider != normalized.provider:
            raise ProviderConfigurationError(
                "provider adapter factory does not match configuration"
            )

        credential = secret_source.resolve(normalized.credential_ref)
        if not credential.strip():
            raise ProviderConfigurationError("provider credential is unavailable")

        try:
            adapter = factory.create(normalized, credential)
        except Exception:
            raise ProviderConfigurationError("provider adapter construction failed") from None

        self._validate_adapter(normalized, adapter)
        return adapter

    @classmethod
    def validate(cls, configuration: ProviderConfiguration) -> ProviderConfiguration:
        """Normalize non-secret settings and reject unsafe capability declarations."""
        provider = cls._required(configuration.provider, "provider").casefold()
        credential_ref = cls._required(
            configuration.credential_ref,
            "credential_ref",
        )
        media_types = tuple(
            cls._required(item, "media_type").casefold() for item in configuration.media_types
        )
        if not media_types:
            raise ProviderConfigurationError("at least one media_type is required")
        if len(media_types) != len(set(media_types)):
            raise ProviderConfigurationError("provider media_types must be unique")
        unsupported = tuple(item for item in media_types if item not in cls._MEDIA_TYPES)
        if unsupported:
            raise ProviderConfigurationError(f"unsupported provider media_type: {unsupported[0]}")

        options = tuple(
            ProviderOption(
                name=cls._required(item.name, "option name").casefold(),
                value=cls._required(item.value, "option value"),
            )
            for item in configuration.options
        )
        names = tuple(item.name for item in options)
        if len(names) != len(set(names)):
            raise ProviderConfigurationError("provider option names must be unique")
        if configuration.timeout_seconds < 1:
            raise ProviderConfigurationError("timeout_seconds must be at least 1")

        return ProviderConfiguration(
            provider=provider,
            credential_ref=credential_ref,
            media_types=media_types,
            model=configuration.model.strip(),
            endpoint=configuration.endpoint.strip(),
            timeout_seconds=configuration.timeout_seconds,
            options=options,
        )

    @staticmethod
    def _validate_adapter(
        configuration: ProviderConfiguration,
        adapter: ProviderExecutionAdapter,
    ) -> None:
        provider = adapter.provider.strip().casefold()
        media_types = tuple(item.strip().casefold() for item in adapter.media_types)
        if provider != configuration.provider:
            raise ProviderConfigurationError(
                "constructed adapter does not match configured provider"
            )
        if not media_types or any(item not in configuration.media_types for item in media_types):
            raise ProviderConfigurationError("constructed adapter exceeds configured capabilities")

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ProviderConfigurationError(f"{field} must not be empty")
        return normalized
