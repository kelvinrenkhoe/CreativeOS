# Provider Execution Adapters

Provider execution is the controlled boundary between an approved CreativeOS asset plan and an
external image or video generation system. The core service is provider-neutral and does not
contain credentials, SDK calls, provider prompt syntax, or storage behaviour.

## Execution flow

`ExecutionRequest` identifies one asset, work, media type, provider, prompt, and immutable set of
provider parameters. `ExecutionApproval` authorizes that exact asset, media type, and provider.
`ProviderExecutionService` then:

1. normalizes and validates the request;
2. verifies that the human approval matches it;
3. verifies the adapter's provider and media capabilities;
4. asks the adapter to validate without side effects;
5. executes the request only when every check passes;
6. validates the returned receipt against the original request.

```python
receipt = ProviderExecutionService().execute(request, approval, adapter)
```

## Adapter boundary

A provider integration implements `ProviderExecutionAdapter`:

- `provider` declares one normalized provider name;
- `media_types` declares support for `image`, `video`, or both;
- `validate()` reports provider-specific limitations without generation;
- `execute()` performs one approved request and returns an `ExecutionReceipt`.

Future adapters may translate the provider-neutral prompt and parameters into Veo, Runway, Kling,
or image-provider syntax. Credential loading, retries, polling, downloads, and provider SDK usage
belong inside those adapters or their infrastructure—not the domain service.

## Safety boundary

This capability does not choose assets, approve creative work, schedule jobs, publish outputs,
advance campaign lifecycle stages, or record orchestration evidence automatically. The caller
retains the receipt and may reference it when recording approved-assets evidence in campaign
orchestration.
