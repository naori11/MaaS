"""AI Backend Abstraction Layer for Pre-commit Code Reviewer.

Detects and selects the best available backend in order:
1. Antigravity CLI (agy) - Gemini-powered, best quality
2. Codex CLI (codex exec) - OpenAI-powered, fallback
3. Ollama (local HTTP API) - offline tertiary

Provides a unified generate(prompt, system) interface.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = int(os.environ.get("PRECOMMIT_TIMEOUT", "90"))
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = os.environ.get("OLLAMA_PORT", "11434")
OLLAMA_MODEL = os.environ.get("PRECOMMIT_MODEL", "qwen2.5:7b")


def get_antigravity_bin() -> str | None:
    """Find the path to the antigravity (agy) CLI binary."""
    which_path = shutil.which("agy") or shutil.which("agy.exe")
    if which_path:
        return which_path

    # Common Windows install path
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidate = Path(local_app_data) / "agy" / "bin" / "agy.exe"
        if candidate.is_file():
            return str(candidate)

    # User profile fallback
    user_profile = os.environ.get("USERPROFILE", "")
    if user_profile:
        candidate = Path(user_profile) / "AppData" / "Local" / "agy" / "bin" / "agy.exe"
        if candidate.is_file():
            return str(candidate)

    return None


def detect_antigravity() -> bool:
    """Check if antigravity CLI is available and functional."""
    agy_bin = get_antigravity_bin()
    if not agy_bin:
        return False
    try:
        proc = subprocess.run(
            [agy_bin, "--help"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return False


def get_codex_bin() -> str | None:
    """Find the path to the codex CLI binary."""
    which_path = shutil.which("codex") or shutil.which("codex.exe")
    if which_path:
        return which_path

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidate = (
            Path(local_app_data)
            / "Programs"
            / "OpenAI"
            / "Codex"
            / "bin"
            / "codex.exe"
        )
        if candidate.is_file():
            return str(candidate)

    user_profile = os.environ.get("USERPROFILE", "")
    if user_profile:
        candidate = (
            Path(user_profile)
            / "AppData"
            / "Local"
            / "Programs"
            / "OpenAI"
            / "Codex"
            / "bin"
            / "codex.exe"
        )
        if candidate.is_file():
            return str(candidate)

    return None


def detect_codex() -> bool:
    """Check if codex CLI is available and functional."""
    codex_bin = get_codex_bin()
    if not codex_bin:
        return False
    try:
        proc = subprocess.run(
            [codex_bin, "--help"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return False


def detect_ollama() -> bool:
    """Check if Ollama local server is responding."""
    url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def select_backend() -> str | None:
    """Select the AI backend based on environment override or auto priority order.

    Order: antigravity -> codex -> ollama.
    Returns:
        "antigravity", "codex", "ollama", or None if no backend is available.
    """
    override = os.environ.get("PRECOMMIT_AI_BACKEND", "auto").strip().lower()

    if override == "antigravity":
        return "antigravity" if detect_antigravity() else None
    if override == "codex":
        return "codex" if detect_codex() else None
    if override == "ollama":
        return "ollama" if detect_ollama() else None

    # Auto mode: try in order
    if detect_antigravity():
        return "antigravity"
    if detect_codex():
        return "codex"
    if detect_ollama():
        return "ollama"

    return None


def invoke_antigravity(
    prompt: str, system: str | None = None, timeout: int = DEFAULT_TIMEOUT
) -> str | None:
    """Invoke Antigravity CLI via --print or stdin to bypass Windows command-line length limits."""
    agy_bin = get_antigravity_bin()
    if not agy_bin:
        return None

    full_prompt = (
        f"{system}\n\nTask:\n{prompt}"
        if system
        else prompt
    )

    try:
        # Use --print flag per plan spec; stream via stdin if prompt is large to prevent
        # Windows [WinError 206] (command line length > 32KB limit).
        if len(full_prompt) < 8000:
            cmd = [
                agy_bin,
                f"--print={full_prompt}",
                "--output-format",
                "json",
                f"--print-timeout={timeout}s",
            ]
            stdin_input = None
        else:
            cmd = [
                agy_bin,
                "--output-format",
                "json",
                f"--print-timeout={timeout}s",
            ]
            stdin_input = full_prompt

        proc = subprocess.run(
            cmd,
            input=stdin_input,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout + 5,
            check=False,
        )
        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or proc.stdout.strip()
            if os.environ.get("PRECOMMIT_DEBUG") == "1":
                from review_output import safe_print
                safe_print(f"[DEBUG] Antigravity CLI exited with code {proc.returncode}: {err_msg[:200]}")
            return None

        # agy returns JSON with a 'response' field
        try:
            data = json.loads(proc.stdout)
            if isinstance(data, dict) and "response" in data:
                return str(data["response"])
            return proc.stdout
        except json.JSONDecodeError:
            return proc.stdout.strip() if proc.stdout else None
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        if os.environ.get("PRECOMMIT_DEBUG") == "1":
            from review_output import safe_print
            safe_print(f"[DEBUG] Antigravity CLI call failed: {exc}")
        return None


def invoke_codex(
    prompt: str, system: str | None = None, timeout: int = DEFAULT_TIMEOUT
) -> str | None:
    """Invoke Codex CLI in non-interactive exec mode via stdin."""
    codex_bin = get_codex_bin()
    if not codex_bin:
        return None

    full_prompt = (
        f"{system}\n\nTask:\n{prompt}"
        if system
        else prompt
    )

    try:
        proc = subprocess.run(
            [codex_bin, "exec", "-"],
            input=full_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or proc.stdout.strip()
            from review_output import safe_print
            safe_print(f"[WARN] Codex CLI exited with code {proc.returncode}: {err_msg[:200]}")
            return None
        return proc.stdout.strip() if proc.stdout else None
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        from review_output import safe_print
        safe_print(f"[WARN] Codex CLI call failed: {exc}")
        return None


def invoke_ollama(
    prompt: str, system: str | None = None, timeout: int = DEFAULT_TIMEOUT
) -> str | None:
    """Invoke Ollama local API."""
    url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system or "",
        "stream": False,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                return str(body.get("response", ""))
            return None
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def generate(
    prompt: str,
    system: str | None = None,
    backend: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[str | None, str]:
    """Generate response using selected AI backend with automatic fallback.

    Returns:
        (response_text, backend_name_used)
        If all backends fail, returns (None, "skipped").
    """
    target = backend or os.environ.get("PRECOMMIT_AI_BACKEND", "auto").strip().lower()

    if target == "antigravity":
        resp = invoke_antigravity(prompt, system, timeout)
        return (resp, "antigravity") if resp else (None, "skipped")

    if target == "codex":
        resp = invoke_codex(prompt, system, timeout)
        return (resp, "codex") if resp else (None, "skipped")

    if target == "ollama":
        resp = invoke_ollama(prompt, system, timeout)
        return (resp, "ollama") if resp else (None, "skipped")

    # Auto mode: try antigravity -> codex -> ollama
    if detect_antigravity():
        resp = invoke_antigravity(prompt, system, timeout)
        if resp:
            return resp, "antigravity"

    if detect_codex():
        resp = invoke_codex(prompt, system, timeout)
        if resp:
            return resp, "codex"

    if detect_ollama():
        resp = invoke_ollama(prompt, system, timeout)
        if resp:
            return resp, "ollama"

    return None, "skipped"


def parse_json_response(raw: str) -> dict[str, Any] | None:
    """Parse JSON from model response text, stripping markdown codeblocks if present."""
    if not raw:
        return None

    cleaned = raw.strip()
    if "```json" in cleaned:
        parts = cleaned.split("```json", 1)[1]
        cleaned = parts.split("```", 1)[0].strip()
    elif "```" in cleaned:
        parts = cleaned.split("```", 1)[1]
        cleaned = parts.split("```", 1)[0].strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        # Fallback: look for first { and last }
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(raw[start : end + 1])
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, ValueError) as err:
                logger.debug("Failed fallback JSON parse: %s", err)

    return None
