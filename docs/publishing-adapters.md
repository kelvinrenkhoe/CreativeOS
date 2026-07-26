# Publishing Adapters

CreativeOS separates publication policy from platform integrations.

`PublishingService` accepts a provider-neutral `PublicationRequest`, an explicit
`PublicationApproval`, and a platform-specific object implementing the
`PublishingAdapter` protocol. It validates all three before calling the adapter.

## Safety boundary

A publication cannot be handed to an adapter unless:

1. The request contains an asset ID, platform, and content.
2. A named human has approved the same asset and platform.
3. The adapter declares support for that platform.
4. The adapter's own validation returns no errors.

The service also validates the returned receipt. It does not store credentials,
choose an account, generate content, or include any live social-platform
implementation.

## Implementing an adapter

An integration implements three members:

- `platform`: normalized platform name.
- `validate(request)`: provider-specific validation with no external write.
- `publish(request)`: the final provider handoff after approval.

Credential storage, account selection, retries, idempotency keys, and provider API
semantics belong in the concrete adapter. Those integrations should be introduced
in separate, platform-focused pull requests with mocked tests before live testing.
