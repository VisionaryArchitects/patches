# Patches

Patches (a.k.a. Patches O’ Hoolihan) is a relentless error‑fixer agent that lives in your build pipeline. It automatically detects, diagnoses, and fixes common build and runtime errors, using a library of known fixes and optional escalation to cloud LLMs when a problem can’t be solved locally.

## Features

- Monitors build or runtime commands and logs output.
- Matches error messages against a library of regex-based rules and applies corresponding actions (pip installs, environment fixes, directory changes).
- Retries the command automatically until success or maximum retries.
- Supports both Windows and Linux environments with cross-platform venv creation.
- Maintains a fix log and supports escalation to the cloud (OpenAI, Claude, or Gemini) when a problem can’t be resolved.
- Configurable behavior via `patches.yaml` and extensible rule set via `known_fixes.yaml`.

## Usage

1. Copy `patches.py`, `patches.yaml`, `known_fixes.yaml`, and `run_patches.ps1` into your project’s `agents/patches` directory.
2. On Windows, run the helper script:

       pwsh -ExecutionPolicy Bypass -File .\agents\patches\run_patches.ps1

   On Linux/WSL:

       python3 agents/patches/patches.py

3. Patches will locate your project root, ensure a Python 3.11 virtual environment, and start executing your target command (defined in `patches.yaml`).
4. Watch the logs in `agents/patches/patches.log` to see applied fixes and outcomes.
5. Extend `known_fixes.yaml` with additional error patterns and actions as you encounter new issues.

---

Patches is inspired by “If you can dodge a wrench, you can dodge a bug.” It’s meant to be a helpful pit crew member, not a philosopher. Keep him focused on fixing errors and let your other agents handle the higher‑level reasoning.
