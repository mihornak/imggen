<img width="1024" height="168" alt="Nano Banana + Freepik" src="https://github.com/user-attachments/assets/50ccaec4-72fc-4741-bfbf-5131829db13a" />


# imggen

**AI image generation from the terminal.** One command, multiple providers, zero dependencies.

```bash
imggen "a golden retriever wearing a hoodie, studio photography"
```

imggen is a single-file Python CLI that generates images using **Gemini** and **Freepik** AI models. No virtual environments, no pip installs, no config files to write — just add an API key and go.

## Install

**Homebrew:**
```bash
brew install mihornak/imggen/imggen
```

**pipx:**
```bash
pipx install imggen-cli
```

**Direct download:**
```bash
curl -sSL https://raw.githubusercontent.com/mihornak/imggen/main/install.sh | bash
```

## Quick start

```bash
# 1. Add your API key (interactive — takes 10 seconds)
imggen auth

# 2. Generate your first image
imggen "a cat astronaut floating in space, digital art"
#  -> ./01_a_cat_astronaut_floating_in_space.png
```

That's it. The image is saved to your current directory.

### Get an API key

You need a key for at least one provider (both are free to start):

- **Gemini** (default) — [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- **Freepik** — [freepik.com/api](https://www.freepik.com/api)

## What you can do

**Switch models** — choose from fast drafts to high-quality output:
```bash
imggen --model pro "a detailed architectural sketch of a treehouse"
imggen --model freepik:flux-realism "a mountain lake at sunrise"
imggen --list-models   # see all available models
```

**Use reference images** — style transfer, editing, and more:
```bash
imggen --ref photo.jpg "turn this into a watercolor painting"
imggen --ref style.png --ref subject.jpg "apply the style to the subject"
```

**Batch generate** — multiple prompts at once:
```bash
imggen "sunset over mountains" "forest in fog" "waves on rocks"
imggen --list prompts.txt   # one prompt per line
```

**Control output** — custom directory, prefix, and pacing:
```bash
imggen --out ./batch --prefix "campaign_" "prompt 1" "prompt 2"
```

## Models

| Provider | Model | Best for |
|----------|-------|----------|
| gemini | `flash` | Fast iteration (default) |
| gemini | `flash2` | Pro-level quality at flash speed |
| gemini | `pro` | Higher quality, better detail |
| freepik | `mystic` | Artistic styles, supports reference images |
| freepik | `flux` | General purpose |
| freepik | `flux-realism` | Photorealistic output |
| freepik | `flux-fast` | Speed |
| freepik | `imagen-4` | Google Imagen 4 via Freepik |
| freepik | `seedream` | Seedream model |

Use models as `imggen --model <name>` or `imggen --model <provider>:<name>`.

## Options

| Flag | Short | Description |
|------|-------|-------------|
| `--model` | `-m` | Model to use (default: `flash`) |
| `--ref` | `-r` | Reference image (repeatable) |
| `--negative` | `-n` | Negative prompt (Freepik only) |
| `--out` | `-o` | Output directory (default: `.`) |
| `--list` | `-l` | Read prompts from a file |
| `--prefix` | `-p` | Filename prefix |
| `--delay` | `-d` | Seconds between API calls (default: `2`) |
| `--list-models` | | Show all available models |
| `--version` | `-V` | Print version |

## Claude Code integration

If you use [Claude Code](https://claude.ai/claude-code), imggen includes a skill:

```
/generate-image a corgi wearing a denim jacket
/generate-image generate 5 logo variations for a coffee shop called "Bean There"
```

The skill is installed automatically when you run `./install.sh` from a local clone.

## Requirements

- Python 3.9+
- An API key for Gemini and/or Freepik

## License

[MIT](LICENSE)
