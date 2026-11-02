# PC check — 28 October 2026

- Windows 11 Pro, 64-bit, build 10.0.26300.
- Intel Core i7-1165G7; 4 cores, 8 logical processors.
- RAM: 31.8 GB total, 11.6 GB available at the initial check.
- C: 55.2 GB free before setup; D: 11.9 GB free before setup.
- NVIDIA GeForce MX330: 2048 MiB VRAM; driver reported by nvidia-smi: 516.40.
- Intel Iris Xe also present.
- Python 3.13.6 and Python 3.14.4 work. Registered Python 3.12 points to a missing executable.
- Project uses standard Python 3.13.6 in its own .venv; no global Python changes.
- Node.js 24.14.1, npm 11.11.0, Git 2.45.1; unchanged.
- Ollama 0.33.2 was already installed and running.
- Existing gemma4:e4b and gemma4-cpu:latest models were retained.
- Downloaded qwen3:4b-instruct (Ollama digest 0edcdef34593), approximately 2.5 GB.
- Tested with CPU inference and an 8192-token context; ollama ps reported approximately
  3.9 GB loaded model memory. Actual total application memory varies.
- browser-use 0.13.14, pytest-playwright 0.10.0. Exact installed dependencies are in requirements.lock.txt.
- Chromium, headless shell, and FFmpeg were installed using Playwright's installer.
- pip check reported no broken requirements.

No Google Sheet or user QA environment was accessed during setup. Demo evidence
is synthetic and applies only to the local fixture, not to the user's application.
