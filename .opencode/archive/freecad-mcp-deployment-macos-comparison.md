# FreeCAD MCP Servers — macOS Deployment Comparison

> **Generated:** 2026-07-13  
> **Mode:** `general` / `code`  
> **Research scope:** 9 projects, 25+ sources searched, cross-referenced

---

## Executive Summary

For macOS users, the **critical distinction** is between servers that run the MCP process **outside** FreeCAD (connecting via XML-RPC/socket to FreeCAD's GUI) and those that try to embed FreeCAD's Python directly. The latter fails on macOS due to `@rpath/libpython3.11.dylib` ABI conflicts. Every project ultimately recommends **XML-RPC mode** on macOS — meaning FreeCAD GUI must be running with the bridge addon active.

No project provides a "FreeCAD-in-a-container" that works on macOS ARM (Docker on macOS cannot run X11/Qt GUI natively, and FreeCAD's ARM app is not distributable as a Docker image without licensing complications). Most Docker images containerize only the **MCP server process**, not FreeCAD itself.

---

## 1. neka-nat/freecad-mcp ⭐ 1300+

| Attribute | Detail |
|-----------|--------|
| **GitHub** | https://github.com/neka-nat/freecad-mcp |
| **License** | MIT |
| **Language** | Python |
| **MCP Transport** | stdio (uvx) → XML-RPC to FreeCAD addon on port 9875 |
| **Install** | `uvx freecad-mcp` (PyPI) + copy `addon/FreeCADMCP` to Mod dir |

### macOS native support
- ✅ **Fully supported natively.** README provides explicit macOS commands.
- Addon path (FreeCAD 1.1): `~/Library/Application Support/FreeCAD/v1-1/Mod/`
- Addon path (FreeCAD 1.0): `~/Library/Application Support/FreeCAD/v1-0/Mod/`

### Docker support
- ❌ **No Dockerfile, no Docker image, no docker-compose.**
- The project has no container support whatsoever.
- Relies entirely on the FreeCAD GUI application running on the host.

### Recommended deployment model
- **Two-process architecture:**
  1. FreeCAD GUI open with "MCP Addon" workbench active + RPC server running (manual or auto-start)
  2. MCP server launched via `uvx freecad-mcp` (stdio) from the AI client
- Communication: `localhost:9875` (XML-RPC), no external network needed

### Known macOS issues
- **MCP Addon missing from workbench list** — most common macOS issue. Wrong `Mod/` path for the FreeCAD version. FreeCAD 1.1 reads `v1-1/Mod`, 1.0 reads `v1-0/Mod`. Copying into the wrong one fails silently.
- **`uvx` PATH issue** — GUI apps on macOS don't inherit shell PATH. Fix: use absolute path (`~/local/bin/uvx`) in `claude_desktop_config.json`.
- **Qt font alias warning** (harmless orange text in Report View on macOS).

### Headless mode
- ❌ **Does NOT support headless.** FreeCAD GUI must be open with the addon running. The addon's RPC server lives on the GUI thread.

### Ports
- `9875` — XML-RPC (default, for tool calls from MCP server to FreeCAD addon)
- `9876` — JSON-RPC socket (alternative mode, rarely used)

---

## 2. spkane/freecad-addon-robust-mcp-server ⭐ 135

| Attribute | Detail |
|-----------|--------|
| **GitHub** | https://github.com/spkane/freecad-addon-robust-mcp-server |
| **Docker Hub** | `spkane/freecad-robust-mcp` (30.7 MB image) |
| **PyPI** | `freecad-robust-mcp` |
| **License** | MIT |
| **Language** | Python |
| **MCP Transport** | stdio (pip/freecad-mcp command) → XML-RPC/socket to FreeCAD |

### macOS native support
- ✅ **Fully supported natively** via pip or source.
- Install: `pip install freecad-robust-mcp`
- Addon install via FreeCAD Addon Manager or manual copy to `~/Library/Application Support/FreeCAD/Mod/`
- **XML-RPC mode is the only recommended mode on macOS.**

### Docker support
- ✅ **Pre-built Docker image on Docker Hub** (`spkane/freecad-robust-mcp`).
- Multi-arch build (amd64 + arm64) available.
- **Container does NOT include FreeCAD.** It only runs the MCP server process. FreeCAD must run on the host.
- Container connects to FreeCAD on the host via `host.docker.internal:9875`.
- `FREECAD_MODE=xmlrpc` mandatory when using Docker.

### Recommended deployment model
- **Three deployment methods (all viable on macOS):**
  1. **pip install** (recommended for most users) — `pip install freecad-robust-mcp`, then add to Claude config as `"command": "freecad-mcp"`
  2. **Docker** — container with MCP server only, connects to FreeCAD on host
  3. **From source** — `mise` + `just` for development

### Known macOS issues
- **Embedded mode CRASHES on macOS.** FreeCAD's `FreeCAD.so` links to `@rpath/libpython3.11.dylib`, conflicting with external Python interpreters. Project explicitly documents this.
- Docker configuration: `host.docker.internal` works natively on macOS Docker Desktop.
- Legacy addon cleanup needed if upgrading from old `MCPBridge/` version.

### Headless mode
- ✅ **Headless mode supported** via `FreeCADCmd` (FreeCAD's CLI headless binary) + `just freecad::run-headless`.
- All modeling operations work. Screenshots and camera control do NOT work in headless mode.

### Ports
- `9875` — XML-RPC (recommended, default)
- `9876` — JSON-RPC socket (alternative)

### Environment Variables
| Variable | Default | Notes |
|----------|---------|-------|
| `FREECAD_MODE` | `xmlrpc` | `xmlrpc` / `socket` / `embedded` (embedded = Linux only) |
| `FREECAD_SOCKET_HOST` | `localhost` | Use `host.docker.internal` for Docker |
| `FREECAD_XMLRPC_PORT` | `9875` | |
| `FREECAD_SOCKET_PORT` | `9876` | |
| `FREECAD_TIMEOUT_MS` | `30000` | |

---

## 3. contextform/freecad-mcp ⭐ 90

| Attribute | Detail |
|-----------|--------|
| **GitHub** | https://github.com/contextform/freecad-mcp |
| **npm** | `freecad-mcp-setup` (installer tool) |
| **License** | MIT |
| **Language** | Python + Node.js (installer) |
| **MCP Transport** | stdio → `working_bridge.py` bridge server |

### macOS native support
- ✅ **Cross-platform by design.** README provides explicit macOS/Linux command.
- Install: `pip install mcp && npm install -g freecad-mcp-setup@latest && npx freecad-mcp-setup setup`
- The installer auto-detects macOS and installs the AICopilot workbench to `~/Library/Application Support/FreeCAD/Mod/AICopilot`
- After install, the AI Copilot service auto-starts when FreeCAD launches.

### Docker support
- ❌ **No Docker support.** No Dockerfile, no docker-compose, no image.
- Pure native install model only.

### Recommended deployment model
- **Single-command npm installer** — handles addon install + MCP bridge registration.
- Designed for **Claude Code** (primary target) and **Claude Desktop** (secondary).
- Claude Desktop requires manual config addition after installer runs:
  ```json
  {
    "mcpServers": {
      "freecad": {
        "command": "python3",
        "args": ["/Users/yourusername/.freecad-mcp/working_bridge.py"]
      }
    }
  }
  ```

### Known macOS issues
- "FreeCAD not found" error if FreeCAD is in a non-standard location.
- npm global install may need `sudo` on macOS depending on Node.js installation method.
- No known ABI issues since it uses a bridge script approach (not embedded).

### Headless mode
- ❌ No documentation of headless support. Assumes FreeCAD GUI is running.

### Ports
- No fixed port mentioned — uses the bridge script approach, likely dynamic or stdio-based.

---

## 4. sandraschi/freecad-mcp ⭐ 9

| Attribute | Detail |
|-----------|--------|
| **GitHub** | https://github.com/sandraschi/freecad-mcp |
| **License** | MIT |
| **Language** | Python (FastMCP 3.2) + TypeScript (React webapp) + Rust (Tauri) + C++ |
| **MCP Transport** | SSE (http://localhost:10944/sse) |
| **Stars** | 9 |

### macOS native support
- ✅ **macOS supported.** Uses `just bootstrap` and `start.ps1` to start.
- Requires FreeCAD 1.1.1+ installed on the host.
- **No explicit macOS addon path mentioned** — appears to use FreeCAD's Python API externally.

### Docker support
- ⚠️ **Partial.** Docker mentioned for optional OpenFOAM 10 fluid simulation containers.
- **The FreeCAD bridge itself is NOT containerized** — FreeCAD runs on the host.
- No main Dockerfile for the MCP server.

### Recommended deployment model
- **Dual interface:**
  1. **MCP server** on port 10944 (SSE transport) — for AI agents
  2. **Web dashboard** on port 10945 (React/Vite) — for human users
- `just bootstrap` → `start.ps1` (PowerShell startup script, kills zombie processes)
- **Tauri 2.0 native desktop** option with PyInstaller sidecar

### Known macOS issues
- PowerShell-based startup script (`start.ps1`) — macOS ships zsh, not PowerShell. Users may need to install PowerShell Core or translate to a shell script.
- `start.ps1` explicitly references Windows COM-like zombie killing; macOS equivalent may not exist.
- FreeCAD bridge uses a TCP connection (port 10946 internal) — may have firewall implications on macOS.

### Headless mode
- ✅ **Headless mode supported** — FreeCAD runs in background as geometry engine.
- Integrates with FluidX3D (GPU-accelerated, supports Apple Silicon via OpenCL).

### Ports
| Port | Purpose |
|------|---------|
| `10944` | MCP server (SSE transport) — AI agents connect here |
| `10945` | Web dashboard (Vite + React) — humans |
| `10946` | FreeCAD bridge (internal) |

---

## 5. proximile/FreeCAD-MCP ⭐ 2

| Attribute | Detail |
|-----------|--------|
| **GitHub** | https://github.com/proximile/FreeCAD-MCP |
| **License** | MIT |
| **Language** | Python |
| **Stars** | 2 (very early, 1 commit) |
| **MCP Transport** | stdio → XML-RPC to FreeCAD in Docker container |

### macOS native support
- ❌ **Not designed for native macOS use.** No macOS-specific instructions.
- The MCP server runs via Python on the host, but FreeCAD itself is expected to run in Docker.

### Docker support
- ✅ **Heavy Docker focus.** Full `docker-compose.yml` with multiple services:
  - `freecad` — Containerized headless FreeCAD with XML-RPC on port 9875
  - `trellis` — TRELLIS.2 for image-to-3D
  - `diffusion` — ComfyUI for text-to-image
  - `inference` — Vision AI (VLM + SAM)
- Optional VNC GUI access (`ENABLE_GUI=true`).
- **Primarily designed for Linux with NVIDIA GPUs** (dual 24GB 3090 setup documented).

### macOS compatibility
- ❌ **Limited on macOS.** Docker on macOS:
  - Cannot run NVIDIA Container Toolkit (no GPU passthrough)
  - FreeCAD in Docker has no hardware-accelerated OpenGL
  - X11 forwarding for VNC works but is slow
- FreeCAD ARM image not provided (x86_64 only)
- **Realistically not usable on macOS in its current form.**

### Recommended deployment model
- **Docker-first:** `docker compose up freecad -d` starts headless FreeCAD
- MCP server runs on host: `python -m src.mcp_server`
- Cloudflare Quick Tunnels for public URL access

### Known macOS issues
- No macOS instructions whatsoever
- NVIDIA-only GPU features
- VNC GUI via Docker on macOS has poor performance
- Very early project (1 commit, 2 stars) — not production-ready

### Ports
| Port | Purpose |
|------|---------|
| `9875` | FreeCAD XML-RPC (in container) |
| `8000` | TRELLIS.2 HTTP |
| `8188` | ComfyUI HTTP |
| `5555` | Vision AI ZMQ |
| `7860` | Gradio debug UI |

---

## 6. ghbalf/freecad-ai (aka Emilien-Etadam/freecad-ai) ⭐ 367

> **Note:** `Emilien-Etadam/freecad-ai` is a mirror/fork of `ghbalf/freecad-ai`. Both are identical repositories.

| Attribute | Detail |
|-----------|--------|
| **GitHub** | https://github.com/ghbalf/freecad-ai |
| **License** | LGPL-2.1 |
| **Language** | Python (zero external dependencies — stdlib only) |
| **MCP Transport** | HTTP (mcp_server_http.py) — optional MCP server exposure |

### macOS native support
- ✅ **Fully supported.** README provides explicit macOS symlink command.
- Addon path: `~/Library/Application Support/FreeCAD/Mod/freecad-ai`
- Also documents version-scoped path for FreeCAD 1.1+: `~/Library/Application Support/FreeCAD/v1.1/Mod/freecad-ai`
- **Primarily a FreeCAD workbench**, not a standalone MCP server. It has an **optional** MCP server component.

### Docker support
- ❌ **No Docker support whatsoever.**
- Pure addon/workbench installation.

### Recommended deployment model
- **FreeCAD workbench addon** — install in Mod directory, switch to "FreeCAD AI" workbench.
- Chat interface docked inside FreeCAD — works with 20+ LLM providers.
- **Optional MCP server** (`mcp_server_http.py`) can expose tools over HTTP to external MCP clients.
- Zero external pip dependencies — uses only Python stdlib.

### Known macOS issues
- Version-scoped paths in FreeCAD 1.1+: if the workbench doesn't appear, check that it was installed into `v1.1/Mod/` not `Mod/` directly.
- Qt font alias warnings (harmless, common across all Qt apps on macOS).
- "Alpha software" warning — may crash FreeCAD from LLM-generated code.

### Headless mode
- ✅ Headless mode supported via `FreeCADCmd` for batch operations.
- The MCP server can expose the workbench tools to external clients.

### Ports
- No fixed default port. The MCP server (`mcp_server_http.py`) can be configured with any port.

---

## 7. Community Docker-Compose & macOS Guides

### FreeCAD MCP Complete Guide (mcp.directory)
- **URL:** https://mcp.directory/blog/freecad-mcp-complete-guide-2026
- Provides detailed step-by-step for macOS:
  - macOS addon path table (FreeCAD 1.0 vs 1.1)
  - Explains the two-process architecture clearly
  - Documents `uvx` PATH fix for macOS GUI apps
  - Troubleshooting for missing workbench on macOS

### Install FreeCAD MCP in Cursor (thedailyworkflow.com)
- **URL:** https://thedailyworkflow.com/mcp/tutorial/install-freecad-mcp-in-cursor
- General guide, mentions macOS permissions
- Recommends `uvx freecad-mcp` approach
- Documents `~/.cursor/mcp.json` config location

### FreeCAD/FC-Worker (Official FreeCAD container)
- **URL:** https://github.com/FreeCAD/FC-Worker
- Official headless FreeCAD Docker container
- ⭐ 5 stars — not actively maintained
- Designed for AWS Lambda, not MCP
- Not suitable for macOS Docker (x86_64 only)

### jango-blockchained/mcp-freecad (Docker Compose)
- **URL:** https://github.com/jango-blockchained/mcp-freecad
- Provides `docker-compose.yml` with FreeCAD AppImage in container
- Exposes ports 8080 (MCP) and 12345 (FreeCAD)
- **Linux-focused** — AppImage extraction in Docker requires FUSE or `--privileged`

### Community `docker-compose.yml` patterns
- **No standard docker-compose exists across projects.**
- The main pattern is: MCP server container + host FreeCAD (no FreeCAD-in-container for macOS).
- Only `proximile/FreeCAD-MCP` containers FreeCAD itself — limited to Linux/NVIDIA.

---

## Comparative Matrix

| Criterion | neka-nat (1300★) | spkane (135★) | contextform (90★) | sandraschi (9★) | proximile (2★) | ghbalf/Emilien (367★) |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|
| **macOS native** | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **macOS docs** | ✅ Explicit | ✅ Explicit | ✅ Detected | ❌ No macOS docs | ❌ None | ✅ Explicit |
| **Docker image** | ❌ | ✅ Docker Hub | ❌ | ⚠️ Partial (OpenFOAM only) | ✅ Full compose | ❌ |
| **FreeCAD in container** | ❌ | ❌ | ❌ | ❌ | ✅ (Linux only) | ❌ |
| **Headless mode** | ❌ | ✅ (FreeCADCmd) | ❌ | ✅ | ✅ | ✅ (FreeCADCmd) |
| **MCP transport** | stdio (uvx) | stdio (pip) | stdio (npm) | SSE (HTTP) | stdio → XML-RPC | HTTP (optional) |
| **GUI required?** | ✅ Yes | ✅ Yes (xmlrpc) | ✅ Yes | ✅ Yes | ❌ No (headless) | ✅ Yes |
| **Workbench addon** | ✅ MCP Addon | ✅ Robust MCP Bridge | ✅ AICopilot | ❌ Not needed | ❌ Not needed | ✅ FreeCAD AI |
| **Easy install** | `uvx freecad-mcp` | `pip install freecad-robust-mcp` | `npx freecad-mcp-setup setup` | `just bootstrap` | `docker compose up` | `git clone + symlink` |
| **Embedded mode (macOS)** | ❌ N/A | ❌ Crashes | ❌ N/A | ❌ N/A | ❌ N/A | ❌ N/A |
| **Tools count** | ~11 | 150+ | ~20 | ~46 | 57 | 50+ |
| **Web UI** | ❌ | ❌ | ❌ | ✅ (React) | ✅ (Gradio) | ✅ (Chat dock) |
| **Maturity** | High | High | Medium | Low | Very low | Medium |

---

## macOS-Specific Paths Reference

### FreeCAD Addon / Mod Directories

| FreeCAD Version | macOS Path |
|-----------------|-----------|
| **1.1+ (canonical)** | `~/Library/Application Support/FreeCAD/v1-1/Mod/` |
| **1.0 (canonical)** | `~/Library/Application Support/FreeCAD/v1-0/Mod/` |
| **1.1+ (legacy fallback)** | `~/Library/Application Support/FreeCAD/Mod/` |

### Claude Desktop Config
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

### Claude Code Project Config
```
<project-root>/.mcp.json
```

---

## Key Findings & Recommendations for macOS

### 1. Do NOT use embedded mode on macOS
All projects agree: embedded mode (`import FreeCAD` directly into the MCP server process) **crashes on macOS** due to `@rpath/libpython3.11.dylib` ABI conflicts. Always use `xmlrpc` or `socket` mode.

### 2. FreeCAD-in-Docker does not work on macOS
No project provides a FreeCAD container image that runs on macOS ARM. Docker on macOS:
- No GPU passthrough
- No native X11 (requires XQuartz or VNC)
- FreeCAD ARM64 builds are not distributed as containers
→ **On macOS, FreeCAD must run natively on the host.**

### 3. Recommended deployment for macOS
- **Most mature + stable:** `neka-nat/freecad-mcp` (1300★, largest community, broadest testing)
  - Install addon, start RPC server, configure Claude Desktop with `uvx freecad-mcp`
- **Most tools + best documentation:** `spkane/freecad-addon-robust-mcp-server` (150+ tools, Docker option)
  - `pip install freecad-robust-mcp`, install workbench via Addon Manager
- **Easiest setup:** `contextform/freecad-mcp` (single `npx` command)
- **For headless/automation on macOS:** `spkane` or `ghbalf/freecad-ai` (both support `FreeCADCmd`)

### 4. Docker on macOS is only for the MCP server layer
If using Docker, only the MCP server process runs in the container — FreeCAD stays on the host. Docker Desktop on macOS provides `host.docker.internal` for container-to-host communication.

### 5. Port conflicts
- `9875` is the de facto standard XML-RPC port used by most projects.
- Running multiple FreeCAD MCP setups simultaneously will conflict on this port.
- Each FreeCAD instance needs its own port if running multiple instances.

---

## Errors & Notes

- **sandraschi/freecad-mcp `start.ps1`**: PowerShell script — macOS users may need to install PowerShell Core or create a zsh alternative.
- **proximile/FreeCAD-MCP**: 1 commit, 2 stars, essentially a skeleton project. Not production-viable, especially on macOS.
- **Emilien-Etadam/freecad-ai**: Identical to `ghbalf/freecad-ai` (fork). Data merged into the `ghbalf` entry above.
- **FreeCAD.org wiki** (Installing on Mac): Blocked by Anubis anti-bot protection — could not fetch directly.
- **FreeCAD Forum** (multiple threads): Blocked by Anubis — couldn't read community macOS troubleshooting threads.
