# Fireball Enterprise Reusable Workflows
Shared GitHub Actions workflows for all Fireball Enterprise repos. Theme repos contain thin callers only — no copied CI YAML.

## Versioning
Tags use the standard `v` prefix: `vmajor.minor.patch` (e.g. `v2.0.0`). Every release is dual-tagged: the exact version (`v2.0.0`) plus a floating major tag (`v2`) that is force-moved to the latest `v2.x.x` release. Callers reference `@v2` to pick up non-breaking updates automatically; pin an exact tag (`@v2.0.0`) only when reproducibility matters more. Breaking changes bump the major and get a new floating tag (e.g. `v3`).

Note: theme repo Releases (cut by `release.yml`) keep Fireball versioning with no `v` prefix (e.g. `1.4.0`) — the prefix applies only to this repo's tags.

Cutting a release: bump `VERSION` (e.g. `2.0.0`) in the PR that changes workflow logic. When it merges to `main`, `publish_release.yml` tags `v2.0.0`, force-moves `v2`, and publishes the GitHub Release. Re-running is safe — it exits early if the tag already exists.

## Workflows
| Workflow | Purpose | Secrets |
|----------|---------|---------|
| `dawn_sync.yml` | Sync caller's `dawn_vanilla` branch with upstream Shopify/dawn (tag or latest) | none |
| `deploy.yml` | Bump VERSION build (dev) and deploy theme to dev/prd | yes — see below |
| `release.yml` | Finalize VERSION, promote development → main, deploy prd, publish GitHub Release | yes — see below |
| `tests.yml` | actionlint, pylint, ruff, theme-check, yamllint | none |

`publish_release.yml` is not reusable — it releases this repo itself (see Versioning above).

## Caller Requirements (deploy/release)
- **Secrets** (per repo, added manually by Levon): `BOT_PRIVATE_KEY`, `SHOPIFY_CLI_THEME_TOKEN`, `SHOPIFY_FLAG_STORE`, `SHOPIFY_THEME_ID_DEV`, `SHOPIFY_THEME_ID_PRD`
- **Variables**: `BOT_APP_ID` (`fireball-actions-bot` is installed org-wide)
- **Branches**: `development` (working), `main` (production), `dawn_vanilla` (pristine Dawn)
- **Tooling**: `uv` + invoke tasks `ver.project_bump_build`, `ver.project_bump_release`, `shopify.deploy`, `tests.*`

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
    uses: fireballenterprise/workflows/.github/workflows/deploy.yml@v2
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
    uses: fireballenterprise/workflows/.github/workflows/tests.yml@v2
```

`.github/workflows/release.yml`:

```yaml
---
name: Release
on:
  workflow_dispatch:

jobs:
  release:
    # called workflows can't elevate beyond the caller's grant (repo default is read-only);
    # promote pushes main and publish creates the Release
    permissions:
      contents: write
    uses: fireballenterprise/workflows/.github/workflows/release.yml@v2
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
    - cron: "0 12 * * 1"  # weekly Monday (template repo only; brand repos run on demand)

jobs:
  dawn_sync:
    # called workflows can't elevate beyond the caller's grant (repo default is read-only);
    # the sync job pushes to dawn_vanilla
    permissions:
      contents: write
    uses: fireballenterprise/workflows/.github/workflows/dawn_sync.yml@v2
    with:
      version: ${{ inputs.version || 'latest' }}
```
