from dataclasses import dataclass, field

import pytest

from services.provider_configuration import (
    EnvironmentSecretSource,
    ProviderConfiguration,
    ProviderConfigurationError,
    ProviderConfigurationService,
    ProviderOption,
)
from services.provider_execution import (
    ExecutionReceipt,
    ExecutionRequest,
)


@dataclass
class FakeAdapter:
    provider: str = "open-video"
    media_types: tuple[str, ...] = ("video",)

    def validate(self, request: ExecutionRequest) -> tuple[str, ...]:
        return ()

    def execute(self, request: ExecutionRequest) -> ExecutionReceipt:
        return ExecutionReceipt(
            request_id=request.request_id,
            asset_id=request.asset_id,
            media_type=request.media_type,
            provider=request.provider,
            external_id="generation-123",
        )


@dataclass
class FakeFactory:
    provider: str = "open-video"
    received_configuration: ProviderConfiguration | None = None
    received_credential: str | None = None
    adapter: FakeAdapter = field(default_factory=FakeAdapter)

    def create(
        self,
        configuration: ProviderConfiguration,
        credential: str,
    ) -> FakeAdapter:
        self.received_configuration = configuration
        self.received_credential = credential
        return self.adapter


@dataclass
class FakeSecretSource:
    value: str = "super-secret-provider-key"
    resolved_reference: str | None = None

    def resolve(self, reference: str) -> str:
        self.resolved_reference = reference
        return self.value


def configuration() -> ProviderConfiguration:
    return ProviderConfiguration(
        provider=" Open-Video ",
        credential_ref="OPEN_VIDEO_API_KEY",
        media_types=(" Video ",),
        model=" cinema-v2 ",
        endpoint=" https://provider.example/v1 ",
        timeout_seconds=90,
        options=(
            ProviderOption(name=" Region ", value=" eu-west-2 "),
        ),
    )


def test_resolves_secret_only_for_validated_configuration() -> None:
    source = FakeSecretSource()
    factory = FakeFactory()

    adapter = ProviderConfigurationService().create_adapter(
        configuration(),
        source,
        factory,
    )

    assert adapter is factory.adapter
    assert source.resolved_reference == "OPEN_VIDEO_API_KEY"
    assert factory.received_credential == source.value
    assert factory.received_configuration == ProviderConfiguration(
        provider="open-video",
        credential_ref="OPEN_VIDEO_API_KEY",
        media_types=("video",),
        model="cinema-v2",
        endpoint="https://provider.example/v1",
        timeout_seconds=90,
        options=(ProviderOption(name="region", value="eu-west-2"),),
    )
    assert source.value not in repr(factory.received_configuration)


def test_environment_source_reads_only_the_named_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPEN_VIDEO_API_KEY", "environment-secret")

    resolved = EnvironmentSecretSource().resolve("OPEN_VIDEO_API_KEY")

    assert resolved == "environment-secret"


def test_missing_environment_secret_uses_generic_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPEN_VIDEO_API_KEY", raising=False)

    with pytest.raises(
        ProviderConfigurationError,
        match="credential is unavailable",
    ):
        EnvironmentSecretSource().resolve("OPEN_VIDEO_API_KEY")


@pytest.mark.parametrize(
    ("invalid", "message"),
    [
        (
            ProviderConfiguration(
                provider="open-video",
                credential_ref="OPEN_VIDEO_API_KEY",
                media_types=(),
            ),
            "at least one media_type",
        ),
        (
            ProviderConfiguration(
                provider="open-video",
                credential_ref="OPEN_VIDEO_API_KEY",
                media_types=("video", " Video "),
            ),
            "unique",
        ),
        (
            ProviderConfiguration(
                provider="open-video",
                credential_ref="OPEN_VIDEO_API_KEY",
                media_types=("audio",),
            ),
            "unsupported",
        ),
        (
            ProviderConfiguration(
                provider="open-video",
                credential_ref="OPEN_VIDEO_API_KEY",
                media_types=("video",),
                timeout_seconds=0,
            ),
            "timeout_seconds",
        ),
    ],
)
def test_rejects_invalid_configuration_before_resolving_secret(
    invalid: ProviderConfiguration,
    message: str,
) -> None:
    source = FakeSecretSource()

    with pytest.raises(ProviderConfigurationError, match=message):
        ProviderConfigurationService().create_adapter(
            invalid,
            source,
            FakeFactory(),
        )

    assert source.resolved_reference is None


def test_rejects_duplicate_non_secret_options() -> None:
    invalid = ProviderConfiguration(
        provider="open-video",
        credential_ref="OPEN_VIDEO_API_KEY",
        media_types=("video",),
        options=(
            ProviderOption(name="region", value="eu-west-2"),
            ProviderOption(name=" Region ", value="us-west-2"),
        ),
    )

    with pytest.raises(ProviderConfigurationError, match="option names"):
        ProviderConfigurationService.validate(invalid)


def test_rejects_factory_or_adapter_capability_mismatch() -> None:
    service = ProviderConfigurationService()
    source = FakeSecretSource()

    with pytest.raises(ProviderConfigurationError, match="factory"):
        service.create_adapter(
            configuration(),
            source,
            FakeFactory(provider="another-provider"),
        )

    assert source.resolved_reference is None

    with pytest.raises(ProviderConfigurationError, match="capabilities"):
        service.create_adapter(
            configuration(),
            source,
            FakeFactory(adapter=FakeAdapter(media_types=("image",))),
        )


def test_factory_failure_does_not_expose_secret() -> None:
    secret = "never-print-this-provider-key"

    class FailingFactory(FakeFactory):
        def create(
            self,
            configuration: ProviderConfiguration,
            credential: str,
        ) -> FakeAdapter:
            raise RuntimeError(f"provider rejected {credential}")

    with pytest.raises(ProviderConfigurationError) as captured:
        ProviderConfigurationService().create_adapter(
            configuration(),
            FakeSecretSource(value=secret),
            FailingFactory(),
        )

    assert str(captured.value) == "provider adapter construction failed"
    assert secret not in str(captured.value)
    assert captured.value.__cause__ is None


def test_blank_secret_from_custom_source_is_rejected() -> None:
    with pytest.raises(ProviderConfigurationError, match="credential is unavailable"):
        ProviderConfigurationService().create_adapter(
            configuration(),
            FakeSecretSource(value=" "),
            FakeFactory(),
        )
