"""imggen — Generate images using multiple AI providers.

Providers:
    gemini   — Google Gemini (Nano Banana) image generation
    freepik  — Freepik AI image generation (Mystic, Flux, Imagen-4, Seedream)

Usage:
    imggen "a photo of a sunset over mountains"
    imggen --model pro "a high-res portrait"
    imggen --model freepik:flux "a cat in space"
    imggen --ref photo.jpg "make this look like a watercolor painting"
    imggen --list-models
    imggen auth
    imggen auth --status

Auth:
    Keys resolved in order: env var → config file → error.
    Config file: ~/.config/imggen/keys.json
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import stat
import sys
import time
import urllib.request
import urllib.error

__version__ = "0.3.0"

# ---------------------------------------------------------------------------
# Provider / model registries
# ---------------------------------------------------------------------------

PROVIDERS = {
    "gemini": {
        "flash": "gemini-2.5-flash-image",
        "flash2": "gemini-3.1-flash-image-preview",
        "pro": "gemini-3-pro-image-preview",
    },
    "freepik": {
        "mystic": "mystic",
        "flux-fast": "flux-fast",
        "flux": "flux",
        "flux-realism": "flux-realism",
        "imagen-4": "imagen-4",
        "seedream": "seedream",
    },
}

# Bare aliases resolve to (provider, alias) — backward compat
BARE_ALIASES = {
    "flash": ("gemini", "flash"),
    "flash2": ("gemini", "flash2"),
    "pro": ("gemini", "pro"),
}

PROVIDER_ENV_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "freepik": "FREEPIK_API_KEY",
}

DEFAULT_PROVIDER = "gemini"
DEFAULT_ALIAS = "flash"

CONFIG_DIR = os.path.expanduser("~/.config/imggen")
CONFIG_FILE = os.path.join(CONFIG_DIR, "keys.json")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
FREEPIK_BASE_URL = "https://api.freepik.com/v1/ai"

# Freepik async models (use task-based polling)
FREEPIK_ASYNC_MODELS = {"mystic"}

# Aspect ratio support
GEMINI_ASPECT_RATIOS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}

FREEPIK_ASPECT_MAP = {
    "1:1": "square_1_1",
    "2:3": "portrait_2_3",
    "3:2": "standard_3_2",
    "3:4": "traditional_3_4",
    "4:3": "classic_4_3",
    "4:5": "social_post_4_5",
    "5:4": "social_5_4",
    "9:16": "social_story_9_16",
    "16:9": "widescreen_16_9",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def slugify(text: str, max_len: int = 50) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text[:max_len]


MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def encode_image(path: str) -> tuple[str, str]:
    """Read an image file and return (base64_data, mime_type)."""
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Reference image not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    mime = MIME_MAP.get(ext) or mimetypes.guess_type(path)[0] or "image/jpeg"
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return data, mime


def api_request(url: str, data: dict | None = None, headers: dict | None = None,
                method: str = "POST", timeout: int = 180) -> dict:
    """Make an HTTP request and return parsed JSON."""
    body = json.dumps(data).encode() if data is not None else None
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode(errors="replace")
        raise RuntimeError(f"API error {e.code}: {resp_body}") from e
    return json.loads(resp.read())


# ---------------------------------------------------------------------------
# Config file (keys.json)
# ---------------------------------------------------------------------------


def load_config() -> dict:
    if not os.path.isfile(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(cfg: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    os.chmod(CONFIG_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 600


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------


def resolve_model(raw: str) -> tuple[str, str, str]:
    """Resolve a model spec to (provider, alias, model_id).

    Accepts:
        "flash"            → bare alias lookup
        "pro"              → bare alias lookup
        "gemini:flash"     → explicit provider:alias
        "freepik:flux"     → explicit provider:alias
    """
    if ":" in raw:
        provider, alias = raw.split(":", 1)
        if provider not in PROVIDERS:
            die(f"Unknown provider '{provider}'. Available: {', '.join(PROVIDERS)}")
        if alias not in PROVIDERS[provider]:
            aliases = ", ".join(PROVIDERS[provider])
            die(f"Unknown model '{alias}' for provider '{provider}'. Available: {aliases}")
        return provider, alias, PROVIDERS[provider][alias]

    if raw in BARE_ALIASES:
        provider, alias = BARE_ALIASES[raw]
        return provider, alias, PROVIDERS[provider][alias]

    # Check if it's an alias in any provider
    for provider, models in PROVIDERS.items():
        if raw in models:
            return provider, raw, models[raw]

    all_aliases = []
    for p, models in PROVIDERS.items():
        for a in models:
            all_aliases.append(f"{p}:{a}")
    die(f"Unknown model '{raw}'. Use --list-models to see available models.")


def get_api_key(provider: str) -> str:
    """Get API key: env var → config file → error."""
    env_key = PROVIDER_ENV_KEYS.get(provider)
    if env_key:
        val = os.environ.get(env_key, "").strip()
        if val:
            return val

    cfg = load_config()
    val = cfg.get(provider, "").strip()
    if val:
        return val

    env_name = PROVIDER_ENV_KEYS.get(provider, f"{provider.upper()}_API_KEY")
    die(f"No API key found for '{provider}'.\n"
        f"  Set {env_name} env var, or run: imggen auth")


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------


def generate_gemini(prompt: str, model_id: str, api_key: str,
                    ref_images: list[str] | None = None,
                    negative: str | None = None,
                    aspect_ratio: str | None = None) -> tuple[bytes, str]:
    """Call the Gemini API. Returns (image_bytes, extension)."""
    endpoint = f"{GEMINI_BASE_URL}/{model_id}:generateContent?key={api_key}"

    parts: list[dict] = []
    for img_path in (ref_images or []):
        b64, mime = encode_image(img_path)
        parts.append({"inline_data": {"mime_type": mime, "data": b64}})
    parts.append({"text": prompt})

    gen_config: dict = {"responseModalities": ["image", "text"]}
    if aspect_ratio:
        if aspect_ratio not in GEMINI_ASPECT_RATIOS:
            raise ValueError(f"Gemini does not support aspect ratio '{aspect_ratio}'. "
                             f"Supported: {', '.join(sorted(GEMINI_ASPECT_RATIOS))}")
        gen_config["imageConfig"] = {"aspectRatio": aspect_ratio}

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": gen_config,
    }

    body = api_request(endpoint, payload)

    for candidate in body.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime = inline.get("mimeType", "image/png")
                ext = "png" if "png" in mime else "jpg"
                return base64.b64decode(inline["data"]), ext

    raise RuntimeError(f"No image returned. Response: {json.dumps(body, indent=2)[:500]}")


# ---------------------------------------------------------------------------
# Freepik provider
# ---------------------------------------------------------------------------


def generate_freepik_sync(prompt: str, model_id: str, api_key: str,
                          negative: str | None = None,
                          aspect_ratio: str | None = None) -> tuple[bytes, str]:
    """Call the Freepik sync text-to-image API. Returns (image_bytes, extension)."""
    endpoint = f"{FREEPIK_BASE_URL}/text-to-image"
    headers = {"x-freepik-api-key": api_key}

    image_size = "square_1_1"
    if aspect_ratio:
        if aspect_ratio not in FREEPIK_ASPECT_MAP:
            raise ValueError(f"Freepik does not support aspect ratio '{aspect_ratio}'. "
                             f"Supported: {', '.join(sorted(FREEPIK_ASPECT_MAP))}")
        image_size = FREEPIK_ASPECT_MAP[aspect_ratio]

    payload = {
        "prompt": prompt,
        "num_images": 1,
        "image_size": image_size,
        "model": model_id,
    }
    if negative:
        payload["negative_prompt"] = negative

    body = api_request(endpoint, payload, headers=headers)

    for item in body.get("data", []):
        b64 = item.get("base64")
        if b64:
            return base64.b64decode(b64), "png"

    raise RuntimeError(f"No image returned. Response: {json.dumps(body, indent=2)[:500]}")


def generate_freepik_mystic(prompt: str, api_key: str,
                            ref_images: list[str] | None = None,
                            negative: str | None = None,
                            aspect_ratio: str | None = None) -> tuple[bytes, str]:
    """Call the Freepik Mystic async API. Returns (image_bytes, extension)."""
    endpoint = f"{FREEPIK_BASE_URL}/mystic"
    headers = {"x-freepik-api-key": api_key}

    payload = {
        "prompt": prompt,
        "num_images": 1,
        "resolution": "2k",
    }
    if aspect_ratio:
        if aspect_ratio not in FREEPIK_ASPECT_MAP:
            raise ValueError(f"Freepik does not support aspect ratio '{aspect_ratio}'. "
                             f"Supported: {', '.join(sorted(FREEPIK_ASPECT_MAP))}")
        payload["aspect_ratio"] = FREEPIK_ASPECT_MAP[aspect_ratio]
    if negative:
        payload["negative_prompt"] = negative

    # Mystic supports style_reference + structure_reference (first 2 ref images)
    if ref_images:
        b64_first, _ = encode_image(ref_images[0])
        payload["styling"] = {"style_reference": {"image": b64_first}}
        if len(ref_images) >= 2:
            b64_second, _ = encode_image(ref_images[1])
            payload["styling"]["structure_reference"] = {"image": b64_second}
        if len(ref_images) > 2:
            print(f"  Warning: Mystic supports max 2 reference images, ignoring {len(ref_images) - 2} extra",
                  file=sys.stderr)

    # Submit task
    body = api_request(endpoint, payload, headers=headers)
    task_id = body.get("task_id") or body.get("data", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in Mystic response: {json.dumps(body, indent=2)[:500]}")

    # Poll for result
    poll_url = f"{FREEPIK_BASE_URL}/mystic/{task_id}"
    poll_headers = {"x-freepik-api-key": api_key}
    deadline = time.time() + 120
    while time.time() < deadline:
        time.sleep(3)
        result = api_request(poll_url, data=None, headers=poll_headers, method="GET")
        status = result.get("status") or result.get("data", {}).get("status", "")
        if status == "COMPLETED":
            for item in result.get("data", {}).get("images", result.get("data", {}).get("data", [])):
                b64 = item.get("base64")
                if b64:
                    return base64.b64decode(b64), "png"
            raise RuntimeError(f"Mystic completed but no image found: {json.dumps(result, indent=2)[:500]}")
        if status in ("FAILED", "ERROR"):
            raise RuntimeError(f"Mystic task failed: {json.dumps(result, indent=2)[:500]}")
        sys.stdout.write(".")
        sys.stdout.flush()

    raise RuntimeError("Mystic task timed out after 120s")


def generate_freepik(prompt: str, model_id: str, api_key: str,
                     ref_images: list[str] | None = None,
                     negative: str | None = None,
                     aspect_ratio: str | None = None) -> tuple[bytes, str]:
    """Dispatch to sync or async Freepik API."""
    if model_id in FREEPIK_ASYNC_MODELS:
        return generate_freepik_mystic(prompt, api_key, ref_images=ref_images,
                                       negative=negative, aspect_ratio=aspect_ratio)

    # Sync models don't support reference images
    if ref_images:
        print(f"  Warning: Freepik '{model_id}' does not support reference images — ignoring --ref",
              file=sys.stderr)

    return generate_freepik_sync(prompt, model_id, api_key, negative=negative,
                                 aspect_ratio=aspect_ratio)


# ---------------------------------------------------------------------------
# Generator dispatch
# ---------------------------------------------------------------------------

GENERATORS = {
    "gemini": generate_gemini,
    "freepik": generate_freepik,
}


# ---------------------------------------------------------------------------
# auth subcommand
# ---------------------------------------------------------------------------


def mask_key(key: str) -> str:
    if len(key) <= 8:
        return key[:2] + "***"
    return key[:4] + "..." + key[-4:]


def cmd_auth(argv: list[str]):
    """Handle `imggen auth [provider key] [--status]`."""
    if "--status" in argv:
        cfg = load_config()
        print("imggen auth status\n")
        for provider, env_name in PROVIDER_ENV_KEYS.items():
            env_val = os.environ.get(env_name, "").strip()
            cfg_val = cfg.get(provider, "").strip()
            if env_val:
                print(f"  {provider:10s}  ✓ configured (env: {env_name} = {mask_key(env_val)})")
            elif cfg_val:
                print(f"  {provider:10s}  ✓ configured (config: {mask_key(cfg_val)})")
            else:
                print(f"  {provider:10s}  ✗ not configured")
        print(f"\nConfig file: {CONFIG_FILE}")
        return

    # Non-interactive: imggen auth <provider> <key>
    non_flag = [a for a in argv if not a.startswith("-")]
    if len(non_flag) == 2:
        provider, key = non_flag
        if provider not in PROVIDER_ENV_KEYS:
            die(f"Unknown provider '{provider}'. Available: {', '.join(PROVIDER_ENV_KEYS)}")
        cfg = load_config()
        cfg[provider] = key
        save_config(cfg)
        print(f"Saved {provider} API key to {CONFIG_FILE}")
        return

    if len(non_flag) == 1:
        die(f"Usage: imggen auth <provider> <key>\n"
            f"  Providers: {', '.join(PROVIDER_ENV_KEYS)}")

    # Interactive mode
    print("imggen — API key setup\n")
    cfg = load_config()
    changed = False

    for provider, env_name in PROVIDER_ENV_KEYS.items():
        env_val = os.environ.get(env_name, "").strip()
        cfg_val = cfg.get(provider, "").strip()
        current = env_val or cfg_val

        if current:
            print(f"  {provider}: already configured ({mask_key(current)})")
            try:
                answer = input(f"  Update {provider} key? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if answer not in ("y", "yes"):
                continue

        try:
            key = input(f"  Enter {provider} API key (blank to skip): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if key:
            cfg[provider] = key
            changed = True
            print(f"  ✓ {provider} key saved")
        else:
            print(f"  — skipped {provider}")

    if changed:
        save_config(cfg)
        print(f"\nKeys saved to {CONFIG_FILE}")
    else:
        print("\nNo changes made.")


# ---------------------------------------------------------------------------
# setup-skill subcommand
# ---------------------------------------------------------------------------

SKILL_URL = "https://raw.githubusercontent.com/mihornak/imggen/main/skill/SKILL.md"
SKILL_DIR = os.path.expanduser("~/.claude/skills/generate-image")
SKILL_FILE = os.path.join(SKILL_DIR, "SKILL.md")


def cmd_setup_skill():
    """Download and install the Claude Code skill."""
    claude_dir = os.path.expanduser("~/.claude")
    if not os.path.isdir(claude_dir):
        die("~/.claude not found. Install Claude Code first.")

    print("Installing Claude Code skill...")
    try:
        req = urllib.request.Request(SKILL_URL)
        resp = urllib.request.urlopen(req, timeout=15)
        content = resp.read()
    except Exception as e:
        die(f"Failed to download skill: {e}")

    os.makedirs(SKILL_DIR, exist_ok=True)
    with open(SKILL_FILE, "wb") as f:
        f.write(content)
    print(f"Skill installed to {SKILL_FILE}")
    print("Restart Claude Code to use: /generate-image")


# ---------------------------------------------------------------------------
# --list-models
# ---------------------------------------------------------------------------


def cmd_list_models():
    print("Available models:\n")
    print(f"  {'Provider':<10s}  {'Alias':<14s}  {'Model ID':<30s}  {'Notes'}")
    print(f"  {'─' * 10}  {'─' * 14}  {'─' * 30}  {'─' * 20}")
    for provider, models in PROVIDERS.items():
        for alias, model_id in models.items():
            bare = "  (default)" if (provider, alias) == (DEFAULT_PROVIDER, DEFAULT_ALIAS) else ""
            if alias in BARE_ALIASES:
                bare_note = f"  bare alias OK" if not bare else f"{bare}, bare alias OK"
            else:
                bare_note = bare
            notes = bare_note.strip()
            full = f"{provider}:{alias}"
            print(f"  {provider:<10s}  {full:<14s}  {model_id:<30s}  {notes}")
    print(f"\nUsage: imggen --model <alias>  or  imggen --model <provider>:<alias>")


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------


def load_prompts_from_file(path: str) -> list[str]:
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    # Intercept subcommands before argparse
    if len(sys.argv) >= 2 and sys.argv[1] == "auth":
        cmd_auth(sys.argv[2:])
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "setup-skill":
        cmd_setup_skill()
        return

    parser = argparse.ArgumentParser(
        prog="imggen",
        description="Generate images using multiple AI providers (Gemini, Freepik).",
    )
    parser.add_argument("-V", "--version", action="version",
                        version=f"%(prog)s {__version__}")
    parser.add_argument("prompts", nargs="*", help="One or more image prompts")
    parser.add_argument("--ref", "-r", action="append", default=[], metavar="IMAGE",
                        help="Reference image(s) to include with every prompt (repeatable)")
    parser.add_argument("--list", "-l", metavar="FILE",
                        help="Read prompts from a text file (one per line)")
    parser.add_argument("--model", "-m", default=f"{DEFAULT_ALIAS}",
                        help=f"Model alias or provider:alias (default: {DEFAULT_ALIAS})")
    parser.add_argument("--aspect", "-a", default=None, metavar="W:H",
                        help="Aspect ratio, e.g. 16:9, 9:16, 4:3, 3:4, 1:1 (default: 1:1)")
    parser.add_argument("--negative", "-n", default=None, metavar="PROMPT",
                        help="Negative prompt (Freepik only, ignored by Gemini)")
    parser.add_argument("--out", "-o", default=".", help="Output directory (default: current dir)")
    parser.add_argument("--prefix", "-p", default="", help="Filename prefix for generated images")
    parser.add_argument("--delay", "-d", type=float, default=2.0,
                        help="Delay in seconds between API calls (default: 2)")
    parser.add_argument("--list-models", action="store_true",
                        help="List all available models and exit")

    args = parser.parse_args()

    if args.list_models:
        cmd_list_models()
        return

    # Resolve model
    provider, alias, model_id = resolve_model(args.model)

    # Collect prompts
    prompts: list[str] = []
    if args.list:
        prompts.extend(load_prompts_from_file(args.list))
    if args.prompts:
        prompts.extend(args.prompts)

    if not prompts:
        parser.print_help()
        sys.exit(1)

    # Validate reference images upfront
    for ref in args.ref:
        ref_path = os.path.expanduser(ref)
        if not os.path.isfile(ref_path):
            die(f"Reference image not found: {ref}")

    if args.ref:
        print(f"Using {len(args.ref)} reference image(s): {', '.join(args.ref)}")
        print()

    # Warn if negative prompt used with Gemini
    if args.negative and provider == "gemini":
        print("Note: --negative is not supported by Gemini and will be ignored.", file=sys.stderr)

    # API key
    api_key = get_api_key(provider)

    # Output dir
    os.makedirs(args.out, exist_ok=True)

    total = len(prompts)
    results = []
    gen_fn = GENERATORS[provider]

    for i, prompt in enumerate(prompts, 1):
        slug = slugify(prompt)
        label = f"{args.prefix}{i:02d}_{slug}" if args.prefix else f"{i:02d}_{slug}"

        print(f"[{i}/{total}] Generating ({provider}:{alias}): {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

        try:
            img_bytes, ext = gen_fn(
                prompt, model_id, api_key,
                ref_images=args.ref or None,
                negative=args.negative,
                aspect_ratio=args.aspect,
            )
            path = os.path.join(args.out, f"{label}.{ext}")
            with open(path, "wb") as f:
                f.write(img_bytes)
            abs_path = os.path.abspath(path)
            print(f"  -> {abs_path}")
            results.append(abs_path)
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            results.append(None)

        if i < total:
            time.sleep(args.delay)

    # Summary
    succeeded = sum(1 for r in results if r)
    print(f"\nDone: {succeeded}/{total} images generated in {os.path.abspath(args.out)}/")

    if succeeded < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
