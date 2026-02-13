---
name: generate-image
description: Generate images using Nano Banana (Gemini Image API) or Freepik AI. Use when user asks to generate, create, or make images from text prompts.
allowed-tools: Bash(imggen:*)
argument-hint: <prompt or list of prompts>
---

# Image Generation with imggen

Generate images from text prompts using **Gemini** (Google Nano Banana) or **Freepik** AI providers.

## Environment + auth

- `imggen` CLI must be installed and available on PATH (run `install.sh` from the imggen repo)
- Requires API keys — resolved in order: env var → `~/.config/imggen/keys.json` → error
- Run `imggen auth` to configure keys interactively, or `imggen auth --status` to check
- Do not print, echo, or inspect API keys

## Providers and models

| Provider | Alias | Model ID | Notes |
|----------|-------|----------|-------|
| gemini | `gemini:flash` | gemini-2.5-flash-image | Default. Fast, good for iteration |
| gemini | `gemini:pro` | gemini-3-pro-image-preview | Higher quality, better detail |
| freepik | `freepik:mystic` | mystic | Async. Supports ref images (max 2) |
| freepik | `freepik:flux-fast` | flux-fast | Fast Flux generation |
| freepik | `freepik:flux` | flux | Standard Flux |
| freepik | `freepik:flux-realism` | flux-realism | Photorealistic Flux |
| freepik | `freepik:imagen-4` | imagen-4 | Google Imagen 4 via Freepik |
| freepik | `freepik:seedream` | seedream | Seedream model |

Bare aliases `flash` and `pro` still work for backward compatibility (resolve to Gemini).

## Command patterns

```bash
# Single prompt (default: Gemini flash)
imggen "a photo of a sunset over mountains"

# Multiple prompts as separate arguments
imggen "prompt one" "prompt two" "prompt three"

# Read prompts from a file (one per line)
imggen --list prompts.txt

# Use Nano Banana Pro (higher quality, slower)
imggen --model pro "a detailed portrait"

# Use Freepik Flux
imggen --model freepik:flux "a cat in space, digital art"

# Use Freepik Mystic (async, supports ref images)
imggen --model freepik:mystic "a dreamy landscape"

# Negative prompt (Freepik only)
imggen --model freepik:flux --negative "blurry, low quality" "a sharp photo of a mountain"

# Custom output directory
imggen --out ~/Pictures/ai "a cat in space"

# Add filename prefix
imggen --prefix "project_" "a logo design"

# With a reference image (style transfer, editing, subject reference)
imggen --ref photo.jpg "make this look like a watercolor painting"

# Multiple reference images
imggen --ref style.png --ref subject.jpg "apply the style of the first image to the subject in the second"

# Reference images apply to all prompts in a batch
imggen --ref brand_logo.png "on a coffee mug" "on a t-shirt" "on a tote bag"

# List all available models
imggen --list-models

# Auth setup
imggen auth                          # interactive setup
imggen auth gemini YOUR_KEY          # set a specific key
imggen auth --status                 # check configured providers

# Combine options
imggen --model pro --out ./output --prefix "batch_" "prompt 1" "prompt 2"
```

## CLI reference

```
imggen [OPTIONS] [PROMPTS...]
imggen auth [--status] [PROVIDER KEY]

Options:
  --ref, -r IMAGE       Reference image (repeatable; Gemini: up to 14, Mystic: max 2)
  --list, -l FILE       Read prompts from a text file (one per line)
  --model, -m MODEL     Model alias or provider:alias (default: flash)
  --negative, -n TEXT   Negative prompt (Freepik only, ignored by Gemini)
  --out, -o DIR         Output directory (default: current dir)
  --prefix, -p STR      Filename prefix for generated images
  --delay, -d SECS      Delay between API calls (default: 2)
  --list-models         List all available models and exit
```

## Provider selection guidance

- **Gemini flash** (default): Fast iteration, good quality, supports reference images
- **Gemini pro**: Higher quality, better detail, supports reference images
- **Freepik Mystic**: Creative/artistic styles, supports style + structure reference images (max 2), async
- **Freepik Flux/Flux-realism**: Good for photorealistic images, fast, no ref image support
- **Freepik Imagen-4/Seedream**: Alternative high-quality models, no ref image support

## Reference image support

| Provider | Ref Images | Notes |
|----------|-----------|-------|
| gemini | Yes (up to 14) | Full support |
| freepik (sync models) | No | Warning printed, --ref ignored |
| freepik (mystic) | Partial (max 2) | 1st → style reference, 2nd → structure reference |

## Workflow guidance

1. **Interpret the user's request** — they may provide a single prompt, multiple prompts, or ask you to craft prompts from a description.
2. **Craft prompts if needed** — if the user gives a vague request like "generate some landscape photos", create specific, detailed prompts.
3. **Choose the provider/model** — use `flash` (default) for speed, `pro` for quality. Use Freepik models for specific styles or when the user requests them.
4. **Pick output directory** — default to current dir, or use `--out` to organize. For batch jobs, create a descriptive folder.
5. **Run `imggen`** with the prompts.
6. **Report results** — show the user the file paths of generated images. If any failed, explain the error.

## Handling `$ARGUMENTS`

The user's arguments after `/generate-image` are passed as `$ARGUMENTS`. Interpret them as:

- **A single prompt string**: Run `imggen "$ARGUMENTS"`
- **Multiple prompts separated by newlines or numbered list**: Extract each prompt and pass them all to `imggen`
- **A request to generate prompts**: Craft appropriate prompts first, then run `imggen`
- **Prompt with image paths**: If the user mentions reference images or file paths, extract them as `--ref` flags
- **"--list file.txt"** or similar flags: Pass through directly to `imggen`
- **Model request**: If the user asks for a specific provider/model (e.g., "use Freepik Flux"), pass `--model` accordingly

## Reference images

When the user provides reference images (style references, subjects to edit, photos to transform):

1. **Identify the image paths** from the user's message or conversation context
2. **Pass each as `--ref`** — they'll be sent to the API alongside the text prompt
3. **Choose the right provider** — Gemini supports up to 14 refs, Mystic supports 2, other Freepik models don't support refs
4. **Reference images apply to every prompt** in the batch

### Common use cases for `--ref`
- **Style transfer**: `--ref style.jpg "apply this art style to a cityscape"`
- **Image editing**: `--ref photo.jpg "remove the background and replace with a beach"`
- **Subject consistency**: `--ref character.png "this character riding a bicycle" "this character cooking dinner"`
- **Combining subjects**: `--ref person.jpg --ref background.jpg "place the person in this scene"`

## Tips for good prompts

- Be specific about style: "photorealistic", "watercolor", "3D render", "oil painting"
- Include lighting: "soft studio lighting", "golden hour", "dramatic shadows"
- Mention composition: "close-up", "wide angle", "overhead shot", "centered"
- Add context: "blurred background", "white background", "outdoor setting"
- End with "No text, no typography" if you don't want text in the image
- For Freepik models, use `--negative` to exclude unwanted elements

## Safety + behavior

- Never upload or share generated images without user consent
- Do not generate images of real people by name
- If `imggen` fails with an API error, report it clearly and suggest fixes (check API key, quota, etc.)
- If a key is not configured, tell the user to run: `imggen auth`
