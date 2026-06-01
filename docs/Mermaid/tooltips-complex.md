# Tooltips + Zoom Together

Three complex diagrams, each large enough that auto-detection enables pan/zoom, and each
annotated with per-node hover tooltips. Drag to pan, scroll to zoom, and hover any
labelled node to see its Markdown popup.

## CI/CD pipeline

```mermaid
flowchart TD
    Commit[Git commit] --> Lint{Lint & format}
    Lint -->|pass| Unit[Unit tests]
    Lint -->|fail| Reject[Reject push]
    Unit --> E2E[E2E tests]
    E2E --> Build[Build artifacts]
    Build --> Stage[Deploy to staging]
    Stage --> Smoke{Smoke tests}
    Smoke -->|pass| Prod[Deploy to production]
    Smoke -->|fail| Rollback[Rollback]
    Prod --> Monitor[Monitor metrics]
    Monitor --> Alert{Anomaly?}
    Alert -->|yes| Rollback
    Alert -->|no| Done[Stable release]
```

```mermaid-tooltips
- node: Lint
  text: |
    ### Lint &amp; format

    Runs **ruff** and *ruff-format*. A failure here **blocks** the push.

    See the [contributing guide](https://elgalu.github.io/mkdocs-hover-tooltip-popup/).

    <img src="../../images/assets/mermaid-diagram.png" alt="diagram" width="160">
- node: Unit
  text: "Fast tests with `-m \"not e2e\"`. See the [testing docs](https://elgalu.github.io/mkdocs-hover-tooltip-popup/)."
- node: E2E
  text: "Headless Chromium via *Playwright*. <br>Skipped if no browser is installed."
- node: Prod
  text: "Promotes the artifact to production. Requires green smoke tests."
- node: Rollback
  text: "Reverts to the last stable release. Triggered by failed smoke tests **or** a monitoring anomaly."
```

## Request lifecycle

```mermaid
stateDiagram-v2
    [*] --> Received
    Received --> Authenticated: valid token
    Received --> Rejected: invalid token
    Authenticated --> Authorized: has permission
    Authenticated --> Forbidden: missing permission
    Authorized --> Processing
    Processing --> Cached: cache hit
    Processing --> Computed: cache miss
    Cached --> Responded
    Computed --> Responded
    Responded --> [*]
    Rejected --> [*]
    Forbidden --> [*]
```

```mermaid-tooltips
- node: Authenticated
  text: "The caller's **token** was verified. Identity is known but permissions are not yet checked."
- node: Authorized
  text: "Permission check passed. The request may now touch protected resources."
- node: Processing
  text: |
    #### Processing stage

    Business logic runs here. Supports **bold**, *emphasis*, `inline code`,
    and a [deep link](https://elgalu.github.io/mkdocs-hover-tooltip-popup/Mermaid/).

    ![flow](../../images/assets/mermaid-diagram.png){ width="150" }
- node: Cached
  text: "Served from the cache layer: no recomputation needed."
- node: Computed
  text: "Cache miss: the result is computed fresh and then stored."
```

## Service dependency graph

```mermaid
graph LR
    Gateway[API Gateway] --> Auth[Auth Service]
    Gateway --> Catalog[Catalog Service]
    Gateway --> Cart[Cart Service]
    Catalog --> Search[Search Index]
    Catalog --> DB[(Product DB)]
    Cart --> DB
    Cart --> Pricing[Pricing Service]
    Pricing --> DB
    Auth --> Cache[(Session Cache)]
    Search --> DB
    Pricing --> Promo[Promotions]
    Promo --> DB
```

```mermaid-tooltips
- node: Gateway
  text: |
    ### API Gateway

    Single **entry point**. Routes *every* external request to a downstream service.

    Read the [routing rules](https://elgalu.github.io/mkdocs-hover-tooltip-popup/).

    <img src="../../images/assets/mermaid-diagram.png" alt="topology" width="170">
- node: Auth
  text: "Validates tokens against the [session cache](https://example.com). Stateless otherwise."
- node: Catalog
  text: "Owns product metadata. Reads from the *Product DB* and the search index."
- node: Pricing
  text: "Computes final price including `promotions`. <br>Hot path: heavily cached."
- node: Promo
  text: "Applies active campaigns and discount rules."
```
