# Production Instagram Publishing Adapter

CreativeOS can publish one explicitly approved image or Reel to a configured Instagram
professional account while preserving its provider-neutral publication request and receipt.

## Configuration

- account ID: the destination Instagram professional account
- credential reference: normally `INSTAGRAM_ACCESS_TOKEN`
- endpoint: an explicitly selected Meta Graph API version
- timeout and bounded media-processing polling controls

The access token is resolved only while the factory creates the HTTP transport. It is not copied
into publication requests, approvals, receipts, audit events, logs, or errors.

## Publication lifecycle

The existing `PublishingService` first proves that the named human approved the exact asset and
Instagram destination. The adapter then validates one public HTTPS image or video URL, creates an
Instagram media container, waits for processing to finish, and calls `media_publish`. The returned
Instagram media ID becomes the provider-neutral publication receipt.

Videos are submitted as Reels. Images are submitted as single-image posts. Scheduling, carousels,
stories, music attachment, cross-posting, and caption generation remain outside this milestone.

## Failure and duplicate safety

Validation happens before the first provider write. Failed or expired containers stop without
calling `media_publish`. A processing timeout instructs the operator to reconcile the container
before retrying; CreativeOS does not automatically resubmit an uncertain publication and risk a
duplicate post.

## Operational boundary

This adapter does not choose an account, approve content, upload local files to public hosting,
advance campaign state, or publish to any platform other than the configured Instagram account.
The final `media_publish` call always remains behind the existing explicit human approval.
