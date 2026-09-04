# Fireball Enterprise Shopify Workflows
Shared GitHub Actions workflows for Fireball Enterprise's Shopify theme repos. Theme repos contain thin callers only — no copied CI YAML.

## Versioning
Tags use the standard `v` prefix: `vmajor.minor.patch` (e.g. `v4.0.0`). Every release is dual-tagged: the exact version (`v4.0.0`) plus a floating major tag (`v4`) that is force-moved to the latest `v4.x.x` release. Callers reference `@v4` to pick up non-breaking updates automatically; pin an exact tag (`@v4.0.0`) only when reproducibility matters more. Breaking changes bump the major and get a new floating tag.

**`v4` (2026-09-03) — theme repos are pure content**: caller repos no longer carry any Python tooling (`tasks/`, `modules/`, `pyproject.toml`). The bump + deploy + theme-check logic moved into composite actions in this repo (`actions/{bump-version,deploy-theme,theme-check}`), and `tests.yml` now runs only theme-check + yamllint + actionlint (no `uv`, no `invoke`). Theme `VERSION` files stay plain `X.Y.Z`.

**`v3` (2026-08-28) — the family versioning scheme**: `deploy.yml`'s build-version job bumps the **patch** on every merge to `development`; `release.yml` just promotes + tags whatever `development` is at, unless its `bump` input (`none` | `patch` | `minor` | `major`) forces a milestone.

Note: theme repo Releases (cut by `release.yml`) keep Fireball versioning with no `v` prefix (e.g. `1.5.1`) — the prefix applies only to this repo's tags.

Cutting a release *of this repo*: bump `VERSION` (e.g. `4.1.0`) in the PR that changes workflow logic. When it merges to `main`, `publish_release.yml` tags `v4.1.0`, force-moves `v4`, and publishes the GitHub Release. Re-running is safe — it exits early if the tag already exists.

## Workflows
| Workflow | Purpose | Secrets |
|----------|---------|---------|
| `dawn_sync.yml` | Sync caller's `dawn_vanilla` branch with upstream Shopify/dawn (tag or latest) | none |
| `deploy.yml` | Bump VERSION patch (dev merges) and deploy theme to dev/prd | yes — see below |
| `release.yml` | Promote development → main, deploy prd, publish GitHub Release (optional `bump` input) | yes — see below |
| `tests.yml` | theme-check, yamllint, actionlint | none |

`publish_release.yml` is not reusable — it releases this repo itself (see Versioning above).

`actionlint.yml` is also not reusable — it's a self-test that runs actionlint against this repo's
own workflow YAML on pull requests to `development`/`main`.

## Composite actions (`actions/`)
Referenced fully-qualified (`uses: fireballenterprise/workflows_shopify/actions/<name>@v4`):

| action | inputs | does |
|---|---|---|
| `bump-version` | `part` (patch/minor/major) | bump `VERSION`, output `version` (no commit) |
| `deploy-theme` | `env` (dev/prd) | `npm i -g @shopify/cli` + `shopify theme push` (reads `SHOPIFY_*` from the job env) |
| `theme-check` | — | `npm i -g @shopify/cli` + `shopify theme check` |

## Caller Requirements (deploy/release)
- **Secrets** (per repo, added manually by Levon): `BOT_PRIVATE_KEY`, `SHOPIFY_CLI_THEME_TOKEN`, `SHOPIFY_FLAG_STORE`, `SHOPIFY_THEME_ID_DEV`, `SHOPIFY_THEME_ID_PRD`
- **Variables**: `BOT_APP_ID` (`fireball-actions-bot` is installed org-wide)
- **Branches**: `development` (working), `main` (production), `dawn_vanilla` (pristine Dawn)
- **Files**: `VERSION`, `.theme-check.yml`, `.yamllint`, the theme dirs, and the four thin caller
  workflows below. No `pyproject.toml` / `tasks/` / `modules/`.

## Caller Examples
`.github/workflows/deploy.yml` in a theme repo:

```yaml
---
name: Deploy
on:
  push:
    branches:
      - development
  workflow_dispatch:
    inputs:
      env:
        description: 'Environment'
        required: false
        type: choice
        default: dev
        options:
          - dev
          - prd

jobs:
  deploy:
    uses: fireballenterprise/workflows_shopify/.github/workflows/deploy.yml@v4
    with:
      env: ${{ inputs.env || 'dev' }}
    secrets: inherit
```

`.github/workflows/tests.yml`:

```yaml
---
name: Tests
on:
  pull_request:
    branches:
      - development

jobs:
  tests:
    uses: fireballenterprise/workflows_shopify/.github/workflows/tests.yml@v4
```

`.github/workflows/release.yml`:

```yaml
---
name: Release
on:
  workflow_dispatch:
    inputs:
      bump:
        description: 'Milestone bump on development before promoting'
        type: choice
        default: none
        options: [none, patch, minor, major]

jobs:
  release:
    # called workflows can't elevate beyond the caller's grant (repo default is read-only);
    # promote pushes main and publish creates the Release
    permissions:
      contents: write
    uses: fireballenterprise/workflows_shopify/.github/workflows/release.yml@v4
    with:
      bump: ${{ inputs.bump }}
    secrets: inherit
```

`.github/workflows/dawn_sync.yml`:

```yaml
---
name: Dawn Sync
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Dawn tag or "latest"'
        required: false
        type: string
        default: latest
  schedule:
    - cron: "0 12 1 * *"  # monthly, 1st at 12:00 UTC

jobs:
  dawn_sync:
    # called workflows can't elevate beyond the caller's grant (repo default is read-only);
    # the sync job pushes to dawn_vanilla
    permissions:
      contents: write
    uses: fireballenterprise/workflows_shopify/.github/workflows/dawn_sync.yml@v4
    with:
      version: ${{ inputs.version || 'latest' }}
```
