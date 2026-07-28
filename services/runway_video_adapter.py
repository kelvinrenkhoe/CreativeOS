"""Execute approved video requests through the Runway API."""

import hashlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from services.provider_configuration import (
    ProviderAdapterFactory,
    ProviderConfiguration,
    ProviderConfigurationError,
)
from services.provider_execution import ExecutionReceipt, ExecutionRequest
from services.queue_worker import RetryableProviderError


class RunwayTransport:
    """Small versioned HTTP boundary for Runway task operations."""

    def __init__(self, credential: str, *, endpoint: str, timeout: int) -> None:
        self._credential = credential
        self._endpoint = endpoint.rstrip("/")
        self._timeout = timeout

    def request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> Any:
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{self._endpoint}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self._credential}",
                "Content-Type": "application/json",
                "X-Runway-Version": "2024-11-06",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read())
        except (TimeoutError, urllib.error.URLError) as error:
            raise RetryableProviderError(
                "Runway video generation temporarily failed"
            ) from error
        except urllib.error.HTTPError as error:
            if error.code == 429 or error.code >= 500:
                raise RetryableProviderError(
                    "Runway video generation temporarily failed"
                ) from error
            raise RuntimeError("Runway video generation failed") from error

    def download(self, url: str) -> bytes:
        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as response:
                return response.read()
        except (TimeoutError, urllib.error.URLError) as error:
            raise RetryableProviderError(
                "Runway video download temporarily failed"
            ) from error


class RunwayVideoAdapter:
    """Generate one approved video through a configured Runway transport."""

    _RATIOS = ("1280:720", "720:1280")
    _PARAMETERS = ("duration", "ratio", "prompt_image", "seed")

    def __init__(
        self,
        transport: Any,
        *,
        model: str,
        output_dir: Path,
        poll_interval: float,
        max_polls: int,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._transport = transport
        self._model = self._required(model, "model")
        self._output_dir = output_dir
        self._poll_interval = poll_interval
        self._max_polls = max_polls
        self._sleeper = sleeper

    @property
    def provider(self) -> str:
        return "runway"

    @property
    def media_types(self) -> tuple[str, ...]:
        return ("video",)

    def validate(self, request: ExecutionRequest) -> tuple[str, ...]:
        errors: list[str] = []
        parameters = {item.name: item.value for item in request.parameters}
        unsupported = tuple(name for name in parameters if name not in self._PARAMETERS)
        if unsupported:
            errors.append(f"unsupported Runway video parameter: {unsupported[0]}")
        if parameters.get("ratio", "1280:720") not in self._RATIOS:
            errors.append(f"unsupported Runway video ratio: {parameters['ratio']}")
        if "duration" in parameters:
            try:
                duration = int(parameters["duration"])
            except ValueError:
                errors.append("Runway video duration must be an integer")
            else:
                if not 2 <= duration <= 10:
                    errors.append("Runway video duration must be between 2 and 10")
        if "seed" in parameters:
            try:
                seed = int(parameters["seed"])
            except ValueError:
                errors.append("Runway video seed must be an integer")
            else:
                if not 0 <= seed <= 4_294_967_295:
                    errors.append("Runway video seed is out of range")
        return tuple(errors)

    def execute(self, request: ExecutionRequest) -> ExecutionReceipt:
        parameters = {item.name: item.value for item in request.parameters}
        payload: dict[str, Any] = {
            "model": self._model,
            "promptText": request.prompt,
            "duration": int(parameters.get("duration", "5")),
            "ratio": parameters.get("ratio", "1280:720"),
        }
        if "seed" in parameters:
            payload["seed"] = int(parameters["seed"])
        prompt_image = parameters.get("prompt_image")
        path = "/v1/text_to_video"
        if prompt_image:
            payload["promptImage"] = prompt_image
            path = "/v1/image_to_video"

        created = self._transport.request("POST", path, payload)
        task_id = str(created.get("id", "")).strip()
        if not task_id:
            raise RuntimeError("Runway video generation returned no task ID")

        task = self._wait(task_id)
        outputs = tuple(task.get("output") or ())
        if not outputs or not isinstance(outputs[0], str):
            raise RuntimeError("Runway video generation returned no output")

        request_key = hashlib.sha256(request.request_id.encode()).hexdigest()[:16]
        self._output_dir.mkdir(parents=True, exist_ok=True)
        target = self._output_dir / f"{request_key}.mp4"
        temporary = target.with_suffix(".mp4.tmp")
        temporary.write_bytes(self._transport.download(outputs[0]))
        temporary.replace(target)
        return ExecutionReceipt(
            request_id=request.request_id,
            asset_id=request.asset_id,
            media_type=request.media_type,
            provider=request.provider,
            external_id=f"runway-video:{task_id}",
            outputs=(str(target.resolve()),),
        )

    def _wait(self, task_id: str) -> dict[str, Any]:
        for attempt in range(self._max_polls):
            task = self._transport.request("GET", f"/v1/tasks/{task_id}")
            status = str(task.get("status", "")).upper()
            if status == "SUCCEEDED":
                return task
            if status in ("FAILED", "CANCELED"):
                raise RuntimeError("Runway video generation did not complete")
            if attempt + 1 < self._max_polls:
                self._sleeper(self._poll_interval)
        raise RetryableProviderError("Runway video generation timed out")

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ProviderConfigurationError(f"Runway video {field} must not be empty")
        return normalized


class RunwayVideoAdapterFactory(ProviderAdapterFactory):
    """Construct a Runway adapter without retaining its credential."""

    def __init__(self, transport_factory: Callable[..., Any] = RunwayTransport) -> None:
        self._transport_factory = transport_factory

    @property
    def provider(self) -> str:
        return "runway"

    def create(
        self,
        configuration: ProviderConfiguration,
        credential: str,
    ) -> RunwayVideoAdapter:
        if "video" not in configuration.media_types:
            raise ProviderConfigurationError(
                "Runway video capability is not configured"
            )
        options = {item.name: item.value for item in configuration.options}
        allowed = ("output_dir", "poll_interval", "max_polls")
        unsupported = tuple(name for name in options if name not in allowed)
        if unsupported:
            raise ProviderConfigurationError(
                f"unsupported Runway video configuration option: {unsupported[0]}"
            )
        try:
            poll_interval = float(options.get("poll_interval", "5"))
            max_polls = int(options.get("max_polls", "120"))
        except ValueError as error:
            raise ProviderConfigurationError(
                "invalid Runway polling configuration"
            ) from error
        if poll_interval < 0 or max_polls < 1:
            raise ProviderConfigurationError("invalid Runway polling configuration")

        endpoint = configuration.endpoint or "https://api.dev.runwayml.com"
        transport = self._transport_factory(
            credential,
            endpoint=endpoint,
            timeout=configuration.timeout_seconds,
        )
        return RunwayVideoAdapter(
            transport,
            model=configuration.model or "gen4.5",
            output_dir=Path(options.get("output_dir", ".creativeos/generated/videos")),
            poll_interval=poll_interval,
            max_polls=max_polls,
        )
