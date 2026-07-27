# Real OpenAI Image Provider Adapter

CreativeOS can execute an explicitly approved image request through the OpenAI Image API while
keeping campaign, queue, receipt, and audit models provider-neutral.

## Configuration

Construct the adapter through the existing credential boundary:

- provider: `openai`
- credential reference: `OPENAI_API_KEY`
- media types: `image`
- model: optional; defaults to `gpt-image-2`
- endpoint: optional OpenAI-compatible base URL
- timeout: provider request timeout in seconds
- option `output_dir`: local destination for generated images

The environment secret source resolves `OPENAI_API_KEY` only while the factory constructs the
OpenAI client. The credential value is never copied into an execution request, queue snapshot,
receipt, audit event, output filename, or adapter representation.

## Execution parameters

Approved requests may use these immutable parameters:

- `size`: `auto`, `1024x1024`, `1536x1024`, or `1024x1536`
- `quality`: `auto`, `low`, `medium`, or `high`
- `background`: `auto`, `transparent`, or `opaque`
- `output_format`: `png`, `jpeg`, or `webp`
- `n`: one to four images

Unsupported values are rejected during side-effect-free adapter validation, before the OpenAI
client is called.

## Outputs and receipts

The Image API returns base64 image data. The adapter decodes each result, atomically replaces a
deterministic local file, and returns absolute file paths in the existing `ExecutionReceipt`.
The receipt contains a non-secret OpenAI image execution identifier and the exact CreativeOS
request identity.

A deterministic filename makes a bounded worker retry replace the same logical output instead of
creating an untracked duplicate.

## Failure behaviour

Rate limits, timeouts, connection failures, and OpenAI server failures become
`RetryableProviderError`, allowing the existing queue worker to apply its configured bounded
retry policy. Other provider status failures, malformed responses, and local output errors stop
the job without automatic retry.

Provider error details are not copied into CreativeOS exception text, receipts, or audit events.

## Operational boundary

This milestone adds a real provider call but no automatic campaign transition, background daemon,
publishing action, remote object storage, image editing, or video generation. A queue worker must
still receive an adapter built from valid configuration, and the execution service still
revalidates the matching human approval before any request reaches OpenAI.
