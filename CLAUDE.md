# CLAUDE.md — Development Guide for imggen

## What is this?

`imggen` is a single-file Python 3.9+ CLI (zero dependencies) for generating images via AI APIs (Gemini, Freepik). It's distributed via Homebrew, PyPI, and a curl installer.

## Repository layout

```
imggen                  # The CLI script (source of truth)
imggen_cli.py           # Auto-generated copy without shebang (for PyPI)
pyproject.toml          # PyPI package config (name: imggen-cli)
Makefile                # `make sync` regenerates imggen_cli.py
install.sh              # Installer (symlinks locally, downloads from GitHub when piped)
skill/SKILL.md          # Claude Code skill definition (/generate-image)
.github/workflows/
  release.yml           # Tag push → GitHub Release
  update-homebrew.yml   # Release → updates Homebrew tap formula
  publish-pypi.yml      # Release → publishes to PyPI
```

## Related repositories

| Repo | Purpose |
|------|---------|
| `mihornak/imggen` | This repo. Source code, CI/CD, PyPI package |
| `mihornak/homebrew-imggen` | Homebrew tap. Contains `Formula/imggen.rb` |

The Homebrew tap is auto-updated by `update-homebrew.yml` on each release. You can also update it manually by editing `Formula/imggen.rb` in that repo.

## Secrets

| Secret | Repo | Purpose |
|--------|------|---------|
| `HOMEBREW_TAP_TOKEN` | `mihornak/imggen` | PAT with `repo` + `workflow` scope. Used by `release.yml` to create releases (so downstream workflows trigger) and by `update-homebrew.yml` to push to the tap repo |

The release workflow uses this PAT instead of `GITHUB_TOKEN` because GitHub Actions doesn't trigger downstream workflows from events created by `GITHUB_TOKEN`.

PyPI publishing uses OIDC Trusted Publishers (no token needed), but requires a `pypi` environment configured on the repo.

## Release process

1. Bump `__version__` in `imggen`
2. `make sync` (regenerates `imggen_cli.py`)
3. Commit both files
4. Tag: `git tag vX.Y.Z`
5. Push: `git push && git push origin vX.Y.Z`

This triggers automatically:
- `release.yml` → creates GitHub Release with `imggen` as a downloadable asset
- `update-homebrew.yml` → computes SHA256 of the tarball, updates `Formula/imggen.rb` in the tap repo, commits and pushes
- `publish-pypi.yml` → verifies `imggen_cli.py` is in sync, builds sdist+wheel, publishes via OIDC

Users then get the update via:
- `brew upgrade imggen`
- `pipx upgrade imggen-cli`
- Re-running the curl installer

## Key design decisions

### Single-file architecture
`imggen` is a standalone Python script with a shebang line. No dependencies, no virtualenv. This makes it trivially installable — Homebrew just copies it to bin.

### imggen vs imggen_cli.py
PyPI needs an importable `.py` module. `imggen_cli.py` is an exact copy of `imggen` minus the shebang line. Always regenerate it with `make sync` after editing `imggen`. The PyPI publish workflow verifies they're in sync and fails if they diverge.

### Package name: imggen-cli
The PyPI package is `imggen-cli` (the name `imggen` was taken). The console script entry point is still `imggen`.

### Subcommands vs argparse
`auth` and `setup-skill` are intercepted before argparse in `main()` because they have different argument structures. Everything else goes through the standard argparse flow.

### Aspect ratio mapping
Gemini uses colon-separated ratios natively (`"16:9"`). Freepik uses descriptive strings (`"widescreen_16_9"`). The CLI accepts the user-friendly `W:H` format and maps internally per provider via `FREEPIK_ASPECT_MAP`.

## Claude Code skill

The skill at `skill/SKILL.md` enables `/generate-image` in Claude Code. It's installed to `~/.claude/skills/generate-image/SKILL.md` via:
- `./install.sh` (local clone install)
- `imggen setup-skill` (downloads from GitHub — works for any install method)

When updating the skill, remember that Homebrew users get it via `imggen setup-skill`, which downloads from `main` branch on GitHub. Changes to `skill/SKILL.md` on `main` take effect immediately for anyone who re-runs `setup-skill`.

## Provider APIs

### Gemini
- Endpoint: `generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- Auth: `?key=` query param
- Aspect ratio: `generationConfig.imageConfig.aspectRatio` (colon format)
- Supports reference images via `inline_data` parts

### Freepik (sync models: flux, flux-fast, flux-realism, imagen-4, seedream)
- Endpoint: `api.freepik.com/v1/ai/text-to-image`
- Auth: `x-freepik-api-key` header
- Aspect ratio: `image_size` field (descriptive format like `widescreen_16_9`)
- No reference image support

### Freepik Mystic (async)
- Endpoint: `api.freepik.com/v1/ai/mystic` (POST to create, GET to poll)
- Auth: `x-freepik-api-key` header
- Aspect ratio: `aspect_ratio` field (descriptive format)
- Supports up to 2 reference images (style + structure)
- Polls every 3s, 120s timeout

## Common tasks

### Adding a new model
1. Add to `PROVIDERS` dict in `imggen`
2. If it's a new provider, add to `PROVIDER_ENV_KEYS` and implement a generator function
3. If it's a Freepik async model, add to `FREEPIK_ASYNC_MODELS`
4. Update `skill/SKILL.md` with the new model
5. `make sync` and release

### Adding a new CLI flag
1. Add `parser.add_argument(...)` in `main()`
2. Thread the value through to the generator functions
3. Update `skill/SKILL.md` CLI reference and command patterns
4. `make sync` and release

### Updating the Homebrew formula manually
```bash
git clone https://github.com/mihornak/homebrew-imggen.git
cd homebrew-imggen
# Edit Formula/imggen.rb
git commit -am "description" && git push
```

### Testing a Homebrew install locally
```bash
brew untap mihornak/imggen 2>/dev/null
brew tap mihornak/imggen
brew install imggen
imggen --version
```
