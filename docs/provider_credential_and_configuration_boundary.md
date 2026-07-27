# Provider Credential and Configuration Boundary

CreativeOS can configure media execution providers without placing credential values in
campaign plans, execution requests, queues, receipts, audit events, or persisted snapshots.

## Boundary

`ProviderConfiguration` contains only non-secret settings:

- normalized provider name;
- an opaque `credential_ref`, such as an environment-variable name;
- declared image or video capabilities;
- optional model, endpoint, timeout, and immutable provider options.

The reference is safe to persist and inspect. The referenced credential value is not.

`SecretSource` resolves that reference only when an adapter is being constructed.
`EnvironmentSecretSource` provides the first local-first implementation. Other secret
stores can implement the same protocol without changing domain or queue models.

## Constructing an adapter

1. Build a `ProviderConfiguration` containing no credential value.
2. Select a matching `ProviderAdapterFactory`.
3. Call `ProviderConfigurationService.create_adapter(...)`.
4. The service validates the provider, media types, timeout, and options before accessing
   the secret source.
5. It resolves the credential and passes it directly to the factory.
6. It verifies that the resulting adapter does not exceed the configured capabilities.
7. Pass the returned adapter to the existing `QueueWorkerService`.

The service returns only the adapter. It never returns a credential-bearing configuration
or adds the secret to an execution request.

## Failure safety

Missing credentials use a generic error. Factory exceptions are replaced with a generic
construction error without preserving the original exception chain, preventing a provider
SDK from leaking a credential through its error text. Applications must also avoid placing
credentials in provider adapter `repr` output or custom logs.

## Current limitations

This milestone adds no real image or video provider SDK, remote secret manager, credential
rotation, background daemon, or live generation call. Environment variables are the first
secret source because CreativeOS remains local-first. Later production sources may resolve
references through a managed secret store while preserving this interface.
