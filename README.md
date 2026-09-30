# Fireball Enterprise Shopify Workflows
Shared GitHub Actions workflows for Fireball Enterprise's Shopify theme repos. Theme repos contain thin callers only — no copied CI YAML.

## Versioning
Tags use the standard `v` prefix: `vmajor.minor.patch` (e.g. `v5.0.0`). Every release is dual-tagged: the exact version (`v5.0.0`) plus a floating major tag (`v5`) that is force-moved to the latest `v5.x.x` release. Callers reference `@v5` to pick up non-breaking updates automatically; pin an exact tag (`@v5.0.0`) only when reproducibility matters more. Breaking changes bump the major and get a new floating tag.

**`v5.1.0` (2026-09-29) — live-theme drift guard**: a `prd` deploy no longer blindly overwrites the live theme. After the 2026-09-29 incident (GUI edits made in the Shopify admin were force-pushed away by a release), `deploy_theme` now, for `env: prd`: pulls the live theme (`shopify theme pull`), uploads it as a `live-theme-backup-*` artifact (90 days), and diffs it against the previous release tag (`X.Y.Z` nearest `HEAD`) and the checkout. A live file matching neither is a GUI edit git doesn't have → the job **fails** listing the files (pull them into git — `invoke shopify.pull --site=<site> --env=prd` in fireball_orchestrator — commit, release again). New inputs on `deploy.yml` / `release.yml` / `deploy_theme`: `overwrite_live_edits` (default `false`) and `drift_ignore` (globs Shopify/apps rewrite themselves). Live pushes add `--nodelete` unless every remote-only file was deleted in git on purpose. `deploy.yml`'s checkout now uses `fetch-depth: 0`. Same rules as fireball_orchestrator's local `shopify.deploy` (`modules/shopify/theme_guard.py`).

**`v5` (2026-09-05) — consume `workflows_common`**: the `bump_version` composite action moved to [`workflows_common`](https://github.com/fireballenterprise/workflows_common) (`actions/bump_version@v1`), and `release.yml`'s promote + GitHub-Release jobs are now `workflows_common` reusables (`promote.yml`, `github_release.yml`). Automated commits are authored `Levon Becker <LevonBecker@users.noreply.github.com>`. Behaviour is unchanged — callers just re-point `@v4 → @v5`.

**`v4` (2026-09-03) — theme repos are pure content**: caller repos no longer carry any Python tooling (`tasks/`, `modules/`, `pyproject.toml`). The bump + deploy + theme-check logic moved into composite actions in this repo, and `tests.yml` now runs only theme-check + yamllint + actionlint (no `uv`, no `invoke`). Theme `VERSION` files stay plain `X.Y.Z`.

**`v3` (2026-08-28) — the family versioning scheme**: `deploy.yml`'s build-version job bumps the **patch** on every merge to `development`; `release.yml` just promotes + tags whatever `development` is at, unless its `bump` input (`none` | `patch` | `minor` | `major`) forces a milestone.

Note: theme repo Releases (cut by `release.yml`) keep Fireball versioning with no `v` prefix (e.g. `1.5.1`) — the prefix applies only to this repo's tags.

Cutting a release *of this repo*: bump `VERSION` (e.g. `5.1.0`) in the PR that changes workflow logic. When it merges to `main`, `publish_release.yml` tags `v5.1.0`, force-moves `v5`, and publishes the GitHub Release. Re-running is safe — it exits early if the tag already exists.

## Workflows
| Workflow | Purpose | Secrets |
|----------|---------|---------|
| `dawn_sync.yml` | Sync caller's `dawn_vanilla` branch with upstream Shopify/dawn (tag or latest) | none |
| `deploy.yml` | Bump VERSION patch (dev merges) and deploy theme to dev/prd (prd: drift guard; `overwrite_live_edits`, `drift_ignore` inputs) | yes — see below |
| `release.yml` | Promote development → main, deploy prd, publish GitHub Release (optional `bump`, `overwrite_live_edits`, `drift_ignore` inputs) | yes — see below |
| `tests.yml` | theme-check, yamllint, actionlint | none |

`publish_release.yml` is not reusable — it releases this repo itself (see Versioning above).

`actionlint.yml` is also not reusable — it's a self-test that runs actionlint against this repo's
own workflow YAML on pull requests to `development`/`main`.

## Composite actions (`actions/`)
Referenced fully-qualified (`uses: fireballenterprise/workflows_shopify/actions/<name>@v5`):

| action | inputs | does |
|---|---|---|
| `bump_version` | `part` (patch/minor/major) | bump `VERSION`, output `version` (no commit) |
| `deploy_theme` | `env` (dev/prd), `overwrite_live_edits`, `drift_ignore` | `npm i -g @shopify/cli` + `shopify theme push` (reads `SHOPIFY_*` from the job env). prd: pull live → backup artifact → drift guard (`drift_guard.py`) → push with `--allow-live` (+ `--nodelete` unless remote-only files were deleted in git on purpose) |

### Rolling back a CI prd deploy
Download the run's `live-theme-backup-<theme id>-<run>` artifact, unzip it, then
`shopify theme push --theme <prd id> --store <store> --path <dir> --nodelete --allow-live [--only <file> ...]`
(or, from fireball_orchestrator, `invoke shopify.restore --site=<site> --backup=<unzipped dir> [--files a,b]`).
| `theme_check` | — | `npm i -g @shopify/cli` + `shopify theme check` |

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
    uses: fireballenterprise/workflows_shopify/.github/workflows/deploy.yml@v5
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
    uses: fireballenterprise/workflows_shopify/.github/workflows/tests.yml@v5
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
    uses: fireballenterprise/workflows_shopify/.github/workflows/release.yml@v5
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
    uses: fireballenterprise/workflows_shopify/.github/workflows/dawn_sync.yml@v5
    with:
      version: ${{ inputs.version || 'latest' }}
```
