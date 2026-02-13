<img width="1024" height="400" alt="Nano Banana + Freepik CLI Claude Code skill" src="https://github.com/user-attachments/assets/3401adad-8c4c-4f95-b362-4e0392145e18" />

# imggen

CLI and Claude Code skill for generating images using **Gemini** (Google Nano Banana) and **Freepik** AI providers.

## Installation

### Homebrew

```bash
brew install mihornak/imggen/imggen
```

### pipx / pip

```bash
pipx install imggen-cli    # recommended
# or
pip install imggen-cli
```

### Shell one-liner

```bash
curl -sSL https://raw.githubusercontent.com/mihornak/imggen/main/install.sh | bash
```

### From source

```bash
git clone https://github.com/mihornak/imggen.git
cd imggen
./install.sh
```

The installer will:
- Symlink (or download) the `imggen` CLI to `~/.local/bin/` (override with `--bin /your/path`)
- Install the Claude Code skill to `~/.claude/skills/generate-image/` (local clone only)
- Check that Python 3 is available
- Prompt to configure API keys (via `imggen auth`)

#### Installer options

| Flag | Description |
|------|-------------|
| `--bin DIR` | Install CLI symlink to a custom directory |
| `--no-skill` | Skip Claude Code skill installation |
| `--no-auth` | Skip interactive API key setup |

### Uninstall

```bash
rm ~/.local/bin/imggen
rm -rf ~/.claude/skills/generate-image
rm -rf ~/.config/imggen
```

## Quick start

```bash
# Configure API keys (interactive)
imggen auth

# Generate an image
imggen "a golden retriever wearing a hoodie, studio photography"

# Using Freepik
imggen --model freepik:flux "a cat in space, digital art"
```

## Authentication

API keys are resolved in order: **env var** → **config file** → **error**.

### Option A: `imggen auth` (recommended)

```bash
# Interactive setup — prompts for each provider
imggen auth

# Set a specific provider key
imggen auth gemini YOUR_KEY_HERE
imggen auth freepik YOUR_KEY_HERE

# Check which providers are configured
imggen auth --status
```

Keys are stored in `~/.config/imggen/keys.json` with `600` permissions.

### Option B: Environment variables

```bash
export GEMINI_API_KEY='your-key-here'
export FREEPIK_API_KEY='your-key-here'
```

Add to your shell profile (`~/.zshrc` or `~/.bashrc`) to persist.

### Get API keys

- **Gemini**: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- **Freepik**: [freepik.com/api](https://www.freepik.com/api)

## CLI usage

```
imggen [OPTIONS] [PROMPTS...]
imggen auth [--status] [PROVIDER KEY]
```

### Examples

```bash
# Single image (default: Gemini flash)
imggen "a cat astronaut floating in space, digital art"

# Multiple images
imggen "a sunset over mountains" "a forest in fog" "waves crashing on rocks"

# From a file (one prompt per line)
imggen --list prompts.txt

# Higher quality with Gemini Pro
imggen --model pro "a detailed architectural sketch of a treehouse"

# Freepik Flux (photorealistic)
imggen --model freepik:flux-realism "a mountain lake at sunrise"

# Freepik Mystic (artistic, supports ref images)
imggen --model freepik:mystic "a dreamy watercolor landscape"

# Negative prompt (Freepik only)
imggen --model freepik:flux --negative "blurry, low quality" "a sharp photo of a city"

# Custom output directory + prefix
imggen --out ./batch --prefix "campaign_" "prompt 1" "prompt 2"

# With a reference image (style transfer, editing, etc.)
imggen --ref photo.jpg "turn this into a watercolor painting"

# Multiple reference images
imggen --ref style.png --ref subject.jpg "apply the style to the subject"

# List all available models
imggen --list-models
```

### Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--ref` | `-r` | | Reference image, repeatable |
| `--model` | `-m` | `flash` | Model alias or `provider:alias` |
| `--negative` | `-n` | | Negative prompt (Freepik only) |
| `--out` | `-o` | `.` | Output directory |
| `--list` | `-l` | | Read prompts from a file (one per line) |
| `--prefix` | `-p` | | Filename prefix |
| `--delay` | `-d` | `2` | Seconds between API calls |
| `--list-models` | | | List all models and exit |

## Models

| Provider | Alias | Model ID | Notes |
|----------|-------|----------|-------|
| gemini | `flash` | gemini-2.5-flash-image | Default. Fast, good for iteration |
| gemini | `pro` | gemini-3-pro-image-preview | Higher quality, better detail |
| freepik | `mystic` | mystic | Artistic. Async. Supports ref images (max 2) |
| freepik | `flux-fast` | flux-fast | Fast Flux generation |
| freepik | `flux` | flux | Standard Flux |
| freepik | `flux-realism` | flux-realism | Photorealistic |
| freepik | `imagen-4` | imagen-4 | Imagen 4 via Freepik |
| freepik | `seedream` | seedream | Seedream model |

### Model selection

```bash
imggen --model flash "prompt"             # bare alias (Gemini flash)
imggen --model pro "prompt"               # bare alias (Gemini pro)
imggen --model gemini:flash "prompt"      # explicit provider:alias
imggen --model freepik:flux "prompt"      # Freepik Flux
imggen --model freepik:mystic "prompt"    # Freepik Mystic
```

Bare aliases `flash` and `pro` are shortcuts for the Gemini models (backward compatible).

### Reference image support

| Provider | Ref Images | Notes |
|----------|-----------|-------|
| gemini | Yes (up to 14) | Full support |
| freepik (sync models) | No | Warning printed, `--ref` ignored |
| freepik (mystic) | Partial (max 2) | 1st → style ref, 2nd → structure ref |

## Claude Code skill

After installation, use it in Claude Code:

```
/generate-image a photorealistic image of a corgi wearing a denim jacket
```

You can also give it multiple prompts or ask Claude to craft prompts for you:

```
/generate-image generate 5 variations of a logo for a coffee shop called "Bean There"
```

## Requirements

- Python 3.9+
- API key for at least one provider (Gemini and/or Freepik)
- Claude Code (optional, for the `/generate-image` skill)

## File structure

```
imggen/
├── imggen          # CLI script (Python, no dependencies)
├── install.sh      # Installer
├── skill/
│   └── SKILL.md    # Claude Code skill definition
└── README.md
```
