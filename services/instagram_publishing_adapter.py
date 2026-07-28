"""Publish explicitly approved image and Reel requests through Instagram."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from services.provider_configuration import ProviderConfigurationError, SecretSource
from services.publishing import PublicationReceipt, PublicationRequest


class InstagramPublishingError(RuntimeError):
    """Report a secret-safe Instagram publishing failure."""


@dataclass(frozen=True, slots=True)
class InstagramPublishingConfiguration:
    """Non-secret configuration for one Instagram professional account."""

    account_id: str
    credential_ref: str
    endpoint: str
    timeout_seconds: int = 60
    poll_interval: float = 5
    max_polls: int = 60


class InstagramTransport:
    """Small Graph API boundary that keeps the access token out of payload models."""

    def __init__(self, credential: str, *, endpoint: str, timeout: int) -> None:
        self._credential = credential
        self._endpoint = endpoint.rstrip("/")
        self._timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        values = dict(payload or {})
        values["access_token"] = self._credential
        encoded = urllib.parse.urlencode(values)
        url = f"{self._endpoint}{path}"
        data = None
        if method == "GET":
            url = f"{url}?{encoded}"
        else:
            data = encoded.encode()
        request = urllib.request.Request(url, data=data, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read())
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as error:
            raise InstagramPublishingError("Instagram publishing request failed") from error


class InstagramPublishingAdapter:
    """Create and publish one approved Instagram image or Reel."""

    _IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")
    _VIDEO_SUFFIXES = (".mp4", ".mov")

    def __init__(
        self,
        transport: Any,
        *,
        account_id: str,
        poll_interval: float,
        max_polls: int,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._transport = transport
        self._account_id = self._required(account_id, "account_id")
        self._poll_interval = poll_interval
        self._max_polls = max_polls
        self._sleeper = sleeper

    @property
    def platform(self) -> str:
        return "instagram"

    def validate(self, request: PublicationRequest) -> tuple[str, ...]:
        errors: list[str] = []
        if request.scheduled_for:
            errors.append("Instagram scheduled publishing is not supported")
        if len(request.content) > 2_200:
            errors.append("Instagram caption exceeds 2200 characters")
        if len(request.media) != 1:
            errors.append("Instagram publishing requires exactly one media URL")
            return tuple(errors)

        media_url = request.media[0]
        parsed = urllib.parse.urlparse(media_url)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append("Instagram media must use a public HTTPS URL")
            return tuple(errors)
        suffix = urllib.parse.urlparse(media_url).path.casefold()
        if not suffix.endswith((*self._IMAGE_SUFFIXES, *self._VIDEO_SUFFIXES)):
            errors.append("Instagram media type is not supported")
        return tuple(errors)

    def publish(self, request: PublicationRequest) -> PublicationReceipt:
        media_url = request.media[0]
        is_video = urllib.parse.urlparse(media_url).path.casefold().endswith(self._VIDEO_SUFFIXES)
        payload = {"caption": request.content}
        if is_video:
            payload.update({"media_type": "REELS", "video_url": media_url})
        else:
            payload["image_url"] = media_url

        created = self._transport.request(
            "POST",
            f"/{self._account_id}/media",
            payload,
        )
        container_id = str(created.get("id", "")).strip()
        if not container_id:
            raise InstagramPublishingError("Instagram returned no media container")
        self._wait_until_ready(container_id)

        published = self._transport.request(
            "POST",
            f"/{self._account_id}/media_publish",
            {"creation_id": container_id},
        )
        media_id = str(published.get("id", "")).strip()
        if not media_id:
            raise InstagramPublishingError("Instagram returned no published media ID")
        return PublicationReceipt(platform=self.platform, external_id=media_id)

    def _wait_until_ready(self, container_id: str) -> None:
        for attempt in range(self._max_polls):
            result = self._transport.request(
                "GET",
                f"/{container_id}",
                {"fields": "status_code"},
            )
            status = str(result.get("status_code", "")).upper()
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise InstagramPublishingError("Instagram media processing failed")
            if attempt + 1 < self._max_polls:
                self._sleeper(self._poll_interval)
        raise InstagramPublishingError(
            "Instagram media processing timed out; reconcile before retrying"
        )

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ProviderConfigurationError(f"Instagram publishing {field} must not be empty")
        return normalized


class InstagramPublishingAdapterFactory:
    """Resolve a credential only while constructing the Instagram transport."""

    def __init__(self, transport_factory: Callable[..., Any] = InstagramTransport) -> None:
        self._transport_factory = transport_factory

    def create(
        self,
        configuration: InstagramPublishingConfiguration,
        secret_source: SecretSource,
    ) -> InstagramPublishingAdapter:
        account_id = InstagramPublishingAdapter._required(
            configuration.account_id,
            "account_id",
        )
        credential_ref = InstagramPublishingAdapter._required(
            configuration.credential_ref,
            "credential_ref",
        )
        endpoint = InstagramPublishingAdapter._required(
            configuration.endpoint,
            "endpoint",
        )
        if configuration.timeout_seconds < 1:
            raise ProviderConfigurationError("Instagram timeout_seconds must be at least 1")
        if configuration.poll_interval < 0 or configuration.max_polls < 1:
            raise ProviderConfigurationError("Instagram polling configuration is invalid")

        credential = secret_source.resolve(credential_ref)
        transport = self._transport_factory(
            credential,
            endpoint=endpoint,
            timeout=configuration.timeout_seconds,
        )
        return InstagramPublishingAdapter(
            transport,
            account_id=account_id,
            poll_interval=configuration.poll_interval,
            max_polls=configuration.max_polls,
        )
