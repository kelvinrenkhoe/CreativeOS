# Real Runway Video Provider Adapter

CreativeOS can execute an explicitly approved video request through Runway while keeping campaign,
queue, receipt, and audit models provider-neutral.

## Configuration

- provider: `runway`
- credential reference: `RUNWAYML_API_SECRET`
- media type: `video`
- model: optional; defaults to `gen4.5`
- endpoint: optional; defaults to `https://api.dev.runwayml.com`
- options: `output_dir`, `poll_interval`, and `max_polls`

The credential is resolved only while the factory creates the transport. It is never copied into
an execution request, queue snapshot, receipt, audit event, filename, or error message.

## Request and task lifecycle

The adapter submits text-to-video by default. Adding `prompt_image` selects image-to-video and uses
that URL as the first frame. Approved requests may also set `duration` from 2–10 seconds, `ratio`
to `1280:720` or `720:1280`, and an optional 32-bit unsigned `seed`.

Runway returns a task ID. The adapter polls the versioned task endpoint until `SUCCEEDED`, `FAILED`,
or `CANCELED`, with bounded polling configured outside the request. A successful output is
downloaded to a deterministic local MP4 path and returned with `runway-video:<task-id>` in the
existing execution receipt.

## Failure behaviour

Network failures, rate limits, server errors, and bounded-poll timeouts become
`RetryableProviderError`. Validation errors, provider rejection, cancellation, failed tasks, and
malformed responses stop immediately. Provider response details and credential values are not
copied into CreativeOS errors or audit evidence.

## Operational boundary

This milestone adds video generation and local download only. It does not publish content, advance
campaign lifecycle state, start a background daemon, upload reference media, or bypass the existing
human approval check.
