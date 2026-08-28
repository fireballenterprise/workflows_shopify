# Fireball Enterprise Shopify Workflows
Shared GitHub Actions workflows for Fireball Enterprise's Shopify theme repos. Theme repos contain thin callers only — no copied CI YAML.

## Versioning
Tags use the standard `v` prefix: `vmajor.minor.patch` (e.g. `v3.0.0`). Every release is dual-tagged: the exact version (`v3.0.0`) plus a floating major tag (`v3`) that is force-moved to the latest `v3.x.x` release. Callers reference `@v3` to pick up non-breaking updates automatically; pin an exact tag (`@v3.0.0`) only when reproducibility matters more. Breaking changes bump the major and get a new floating tag.

**`v3` (2026-08-28) — the family versioning scheme** ([[versioning-scheme]] / `fireball_orchestrator`'s `versioning.instructions.md`): `deploy.yml`'s build-version job bumps the **patch** on every merge to `development` (was: an appended `-NNN` build counter); `release.yml` no longer "finalizes" a version — it just promotes + tags whatever `development` is at, unless its new `bump` input (`none` | `patch` | `minor` | `major`, default `none`) forces a milestone. Theme `VERSION` files are plain `X.Y.Z` on both branches, read by `pyproject.toml` via `[tool.setuptools.dynamic]`.

Note: theme repo Releases (cut by `release.yml`) keep Fireball versioning with no `v` prefix (e.g. `1.5.1`) — the prefix applies only to this repo's tags.

Cutting a release *of this repo*: bump `VERSION` (e.g. `3.1.0`) in the PR that changes workflow logic. When it merges to `main`, `publish_release.yml` tags `v3.1.0`, force-moves `v3`, and publishes the GitHub Release. Re-running is safe — it exits early if the tag already exists.

## Workflows
| Workflow | Purpose | Secrets |
|----------|---------|---------|
| `dawn_sync.yml` | Sync caller's `dawn_vanilla` branch with upstream Shopify/dawn (tag or latest) | none |
| `deploy.yml` | Bump VERSION patch (dev merges) and deploy theme to dev/prd | yes — see below |
| `release.yml` | Promote development → main, deploy prd, publish GitHub Release (optional `bump` input) | yes — see below |
| `tests.yml` | actionlint, pylint, ruff, theme-check, yamllint | none |

`publish_release.yml` is not reusable — it releases this repo itself (see Versioning above).

`actionlint.yml` is also not reusable — it's a self-test that runs actionlint against this repo's
own workflow YAML on pull requests to `development`/`main`. `tests.yml`'s jobs assume a caller
repo (Python/uv, theme files) this repo doesn't have, so it isn't triggered directly here.

## Caller Requirements (deploy/release)
- **Secrets** (per repo, added manually by Levon): `BOT_PRIVATE_KEY`, `SHOPIFY_CLI_THEME_TOKEN`, `SHOPIFY_FLAG_STORE`, `SHOPIFY_THEME_ID_DEV`, `SHOPIFY_THEME_ID_PRD`
- **Variables**: `BOT_APP_ID` (`fireball-actions-bot` is installed org-wide)
- **Branches**: `development` (working), `main` (production), `dawn_vanilla` (pristine Dawn)
- **Tooling**: `uv` + invoke tasks `ver.project_bump_{patch,minor,major,build}`, `shopify.deploy`, `tests.*`

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
    uses: fireballenterprise/workflows_shopify/.github/workflows/deploy.yml@v3
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
    uses: fireballenterprise/workflows_shopify/.github/workflows/tests.yml@v3
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
    uses: fireballenterprise/workflows_shopify/.github/workflows/release.yml@v3
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
    uses: fireballenterprise/workflows_shopify/.github/workflows/dawn_sync.yml@v3
    with:
      version: ${{ inputs.version || 'latest' }}
```
