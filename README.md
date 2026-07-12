# Fireball Enterprise Reusable Workflows
Shared GitHub Actions workflows for all Fireball Enterprise repos. Theme repos contain thin callers only — no copied CI YAML.

## Versioning
Tags follow Fireball versioning: NO `v` prefix, `major.minor.patch` (e.g. `1.0.0`). Every release is dual-tagged: the exact version (`1.0.0`) plus a floating major tag (`1`) that is force-moved to the latest `1.x.x` release. Callers reference `@1` to pick up non-breaking updates automatically; pin an exact tag (`@1.0.0`) only when reproducibility matters more. Breaking changes bump the major and get a new floating tag (`2`).

Cutting a release:

```bash
git tag 1.x.y && git tag -f 1
git push origin 1.x.y && git push -f origin 1
```

## Workflows
| Workflow | Purpose | Secrets |
|----------|---------|---------|
| `dawn_sync.yml` | Sync caller's `dawn_vanilla` branch with upstream Shopify/dawn (tag or latest) | none |
| `deploy.yml` | Bump VERSION build (dev) and deploy theme to dev/prd | yes — see below |
| `release.yml` | Finalize VERSION, promote development → main, deploy prd, publish GitHub Release | yes — see below |
| `tests.yml` | actionlint, pylint, ruff, theme-check, yamllint | none |

## Caller Requirements (deploy/release)
- **Secrets** (per repo, added manually by Levon): `BOT_PRIVATE_KEY`, `SHOPIFY_CLI_THEME_TOKEN`, `SHOPIFY_FLAG_STORE`, `SHOPIFY_THEME_ID_DEV`, `SHOPIFY_THEME_ID_PRD`
- **Variables**: `BOT_APP_ID` (`fireball-actions-bot` is installed org-wide)
- **Branches**: `development` (working), `main` (production), `dawn_vanilla` (pristine Dawn)
- **Tooling**: `uv` + invoke tasks `version.bump_build`, `version.bump_release`, `shopify.deploy`, `tests.*`

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
    uses: fireballenterprise/workflows/.github/workflows/deploy.yml@1
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
    uses: fireballenterprise/workflows/.github/workflows/tests.yml@1
```

`.github/workflows/release.yml`:

```yaml
---
name: Release
on:
  workflow_dispatch:

jobs:
  release:
    uses: fireballenterprise/workflows/.github/workflows/release.yml@1
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
    uses: fireballenterprise/workflows/.github/workflows/dawn_sync.yml@1
    with:
      version: ${{ inputs.version || 'latest' }}
```
