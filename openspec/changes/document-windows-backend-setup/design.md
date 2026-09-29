# Design

## Context

`backend/README.md` currently documents a Linux deployment path: uv, Node build, TinyTeX, Chrome, offscreen rendering, environment variables and `backend/scripts/start.sh`. The backend itself is Python 3.10.18 and is intended to run on Linux, but the repository may also be checked out and demoed from Windows.

Windows has different executable names, shell syntax, package-install options and path lookup behavior. The project also has two documentation constraints that must be handled explicitly:

- `backend/scripts/start.sh` is a Bash script, so it cannot be run directly from PowerShell.
- `frontend/package.json` requires Node `^22.18.0 || >=24.12.0`, while the existing backend README dependency table says `Node.js 20+`.

See [proposal.md](proposal.md) for the motivation and scope. This is a documentation-only change; no runtime behavior or API contract changes.

## Goals / Non-Goals

**Goals:**

- Add a Windows setup section to `backend/README.md` that a Windows user can follow end to end.
- Cover PowerShell-native installation/start commands and the Git Bash/WSL alternative for the existing `start.sh`.
- Cover Python/uv, Node/frontend build, environment variables, data directory, network/firewall, report toolchain, Chrome/Kaleido, PyVista offscreen rendering and `/api/health`.
- Make Windows-specific limitations explicit instead of assuming Linux commands work unchanged.

**Non-Goals:**

- Do not modify `backend/scripts/start.sh` or add a PowerShell startup script.
- Do not change API behavior, dependencies, lockfiles, tests or Linux deployment instructions.
- Do not claim Windows support for unverified environments (for example, a Windows server without a usable OpenGL/offscreen environment).
- Do not add Docker, HTTPS, authentication or CI coverage.

## Decisions

### D1: Update `backend/README.md` only, as a separate Windows section

The existing Linux dependency/start section remains the primary deployment path. A new Windows section follows it and reuses the same configuration concepts: Python 3.10.18, uv, the frontend build, `data/`, `PORT`, `WUYE_*` variables and `/api/health`.

Alternative considered: rewrite the whole README as cross-platform. Rejected because the backend is deployed on Linux and rewriting the primary path would add unnecessary churn.

### D2: Recommend PowerShell-native commands first; document Git Bash/WSL for `start.sh`

The Windows section will show native PowerShell steps:

```powershell
cd frontend
npm ci
npm run build

cd ..\backend
uv sync --frozen
$env:PORT = "8000"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

It will also explain that `backend/scripts/start.sh` is Bash and can be used from Git Bash/WSL only; it is not a PowerShell script.

Alternative considered: add a `.ps1` script. Rejected for this change because the user asked for README documentation and a new script would be a separate implementation decision.

### D3: Align the Windows Node requirement with the frontend package metadata

The Windows section will require Node 22.18+ (or the frontend package engine’s compatible newer release) because `frontend/package.json` declares that engine range. The existing `Node.js 20+` dependency-table line is inconsistent with that metadata; it will be corrected to avoid giving Windows users a version that `npm` may reject.

Alternative considered: leave the old Node line and add a warning in the Windows section. Rejected because contradictory version guidance in one README is harder to maintain.

### D4: Document Windows report-toolchain options without pretending TinyTeX’s Unix installer is native

The Windows section will recommend TeX Live or MiKTeX and list the required executables/packages:

- `latexmk`
- `xelatex`
- `ctex`
- Fandol Chinese fonts
- `kpsewhich`

The Linux TinyTeX shell installer may still be used from Git Bash/WSL if the user chooses, but the native Windows path is TeX Live/MiKTeX. The section will tell users to add the TeX `bin` directory to `PATH` and verify with `Get-Command latexmk`, `Get-Command xelatex`, and `kpsewhich`.

Alternative considered: copy the Linux TinyTeX commands into the Windows section. Rejected because those commands are shell-specific and do not represent a native Windows setup.

### D5: Make Chrome/Kaleido and PyVista checks diagnostic, not assumed

Windows commonly installs Chrome outside `PATH`. The backend health check searches for `google-chrome`, `google-chrome-stable`, `chromium`, or `chromium-browser` through `shutil.which`; on Windows the user must ensure the directory containing `chrome.exe` is on `PATH` (or otherwise make a recognized command available). The section will explain how to verify this before relying on PDF generation.

PyVista offscreen screenshot behavior depends on the Windows OpenGL/graphics environment. The README will instruct the user to run `/api/health` and treat `offscreen_rendering` or `chromium` failures as explicit blockers for report generation, rather than assuming a successful server start means reports will work.

Alternative considered: change health checks to search standard Windows install locations. Rejected because this change is documentation-only.

### D6: Include Windows LAN and security caveats

The Windows setup will document:

- bind behavior `0.0.0.0:8000`;
- adding a Windows Firewall inbound rule for the selected port when another machine needs access;
- no login/authentication in the current backend;
- `data/` must be writable and should be placed on a local path without restricted permissions;
- WebGL2 is required for interactive point-cloud preview, although artifact download and computation can still work without it.

Alternative considered: leave networking to a separate operations document. Rejected because Windows users need a complete first-run path in the backend README.

## Risks / Trade-offs

- [Windows commands may differ by Git/uv/TeX installation method] → Keep commands PowerShell-native, list executable checks, and state that Git Bash/WSL is only for `start.sh`.
- [Node 20+ vs Node 22.18+ mismatch] → Correct the README dependency table to match `frontend/package.json`.
- [Chrome is installed but not on PATH] → Document the executable lookup and require a manual PATH verification rather than silently claiming success.
- [MiKTeX/TeX Live package names differ] → List the required commands and packages; instruct users to prioritize `/api/health` output.
- [Windows offscreen rendering may fail without a desktop GPU/driver] → Document it as a report-path blocker and keep the Linux deployment path unchanged.

## Migration Plan

1. Update the Windows section and dependency-table correction in `backend/README.md`.
2. Follow the README from a Windows machine and record any command that fails.
3. Verify `/api/health`, frontend build and a minimal backend startup.
4. If report dependencies are unavailable, document the exact failing check; do not mark the Windows setup as complete.
5. Roll back by removing the added Windows section and restoring the previous Node line.

## Open Questions

None. The planning assumption is that “README” means `backend/README.md`; the Windows instructions will cover backend runtime plus the frontend build artifact that the backend serves.
