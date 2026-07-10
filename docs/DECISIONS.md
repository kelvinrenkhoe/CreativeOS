# Engineering Decisions

A chronological record of significant engineering and product decisions.

---

## 2026-07

### Adopted Layered Architecture

CreativeOS separates presentation, services, domain models and infrastructure.

---

### Introduced ScaffoldService

Reusable scaffolding capability shared by future business services.

---

### Adopted Hierarchical CLI

Commands follow a structured hierarchy.

Examples

creativeos song new

creativeos campaign new

creativeos today

---

### Workspace Summary Service

WorkspaceSummaryService reuses Project as the single source of truth.
