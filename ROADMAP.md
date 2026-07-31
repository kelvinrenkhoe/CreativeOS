# CreativeOS Roadmap

## Phase 8 — Live Campaign Operations

| Story | Status | Tracking |
| --- | --- | --- |
| Campaign runtime status CLI | Complete | #54 / #55 |
| One-action campaign runtime CLI | Complete | #56 / #57 |
| Durable human-review decisions | Complete | #59 / #60 |
| Campaign human-review CLI | Complete | #58 / #61 |
| Campaign resume CLI | In progress | #62 |

The resume command reconciles exactly one uncertain runtime checkpoint from a matching durable human decision. A completed decision requires a persisted provider receipt; a not-completed decision safely reopens the action for a later explicitly configured retry.
