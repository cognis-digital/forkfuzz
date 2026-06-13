<a name="top"></a>
<div align="center">

<img src="https://capsule-render.vercel.app/api?type=rect&color=0:6b46c1,100:2b6cb0&height=120&section=header&text=FORKFUZZ&fontSize=48&fontColor=ffffff&fontAlignY=58" width="100%" alt="FORKFUZZ"/>

# FORKFUZZ

### Mainnet-fork invariant fuzzer that replays your contract against live state and stateful sequences to break protocol invariants before deploy.

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=18&duration=3500&pause=1000&color=6B46C1&center=true&vCenter=true&width=720&lines=Mainnetfork+invariant+fuzzer+that+replays+your+contract+agai;Self-hostable+%C2%B7+MCP-native+%C2%B7+CI-ready+%C2%B7+polyglot" width="720"/>

[![PyPI](https://img.shields.io/pypi/v/cognis-forkfuzz.svg?color=6b46c1)](https://pypi.org/project/cognis-forkfuzz/) [![CI](https://github.com/cognis-digital/forkfuzz/actions/workflows/ci.yml/badge.svg)](https://github.com/cognis-digital/forkfuzz/actions) [![License: COCL 1.0](https://img.shields.io/badge/License-COCL%201.0-2b6cb0.svg)](LICENSE) [![Suite](https://img.shields.io/badge/Cognis-Neural%20Suite-6b46c1.svg)](https://github.com/cognis-digital)

*Web3 & Smart-Contract Security — on-chain safety and analytics.*

</div>

```bash
pip install "git+https://github.com/cognis-digital/forkfuzz.git"
forkfuzz scan .            # → prioritized findings in seconds
```

<!-- cognis:layman:start -->
## What is this?

ForkFuzz is a testing tool for smart contracts and protocol rules — it automatically tries thousands of random action sequences to find combinations that break your stated safety rules before you deploy. You describe your contract's state, functions, and the rules that must always hold (for example, "no account balance can go negative"), and ForkFuzz hunts for the shortest possible sequence of actions that violates one of those rules. It is aimed at developers and security researchers who want to catch logic bugs and edge cases early, without writing exhaustive manual test cases.
<!-- cognis:layman:end -->

## Contents

- [Why forkfuzz?](#why) · [Features](#features) · [Quick start](#quick-start) · [Example](#example) · [Architecture](#architecture) · [AI stack](#ai-stack) · [How it compares](#how-it-compares) · [Integrations](#integrations) · [Install anywhere](#install-anywhere) · [Related](#related) · [Contributing](#contributing)

<a name="why"></a>
## Why forkfuzz?

One-command 'fuzz my contract against real mainnet liquidity' lowers the Echidna learning curve to zero; CI-friendly corpus caching is the hook.

`forkfuzz` is single-purpose, scriptable, and self-hostable: point it at a target, get prioritized results in the format your workflow already speaks (table · JSON · SARIF), gate CI on it, and let agents drive it over MCP.

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="features"></a>
## Features

- ✅ Safe Eval
- ✅ Parse Spec
- ✅ Load Spec
- ✅ Run Sequence
- ✅ Fuzz
- ✅ Runs on Linux/macOS/Windows · Docker · devcontainer
- ✅ Ports in Python, JavaScript, Go, and Rust (`ports/`)

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="quick-start"></a>
<!-- cognis:domains:start -->
## Domains

**Primary domain:** Finance & Quant  ·  **JTF MERIDIAN division:** BLACKBOOK · ORACLE

**Topics:** `cognis` `finance` `fintech` `quant`

Part of the **Cognis Neural Suite** — 300+ source-available tools organized across 12 domains under the JTF MERIDIAN command structure. See the [suite on GitHub](https://github.com/cognis-digital) and [jtf-meridian](https://github.com/cognis-digital/jtf-meridian) for how the pieces fit together.
<!-- cognis:domains:end -->

<!-- cognis:install:start -->
## Install

`forkfuzz` is source-available (not published to PyPI) — every method below installs
straight from GitHub. Pick whichever you prefer; the one-line scripts auto-detect
the best tool available on your machine.

**One-liner (Linux / macOS):**
```sh
curl -fsSL https://raw.githubusercontent.com/cognis-digital/forkfuzz/HEAD/install.sh | sh
```

**One-liner (Windows PowerShell):**
```powershell
irm https://raw.githubusercontent.com/cognis-digital/forkfuzz/HEAD/install.ps1 | iex
```

**Or install manually — any one of:**
```sh
pipx install "git+https://github.com/cognis-digital/forkfuzz.git"     # isolated (recommended)
uv tool install "git+https://github.com/cognis-digital/forkfuzz.git"  # uv
pip install "git+https://github.com/cognis-digital/forkfuzz.git"      # pip
```

**From source:**
```sh
git clone https://github.com/cognis-digital/forkfuzz.git
cd forkfuzz && pip install .
```

Then run:
```sh
forkfuzz --help
```
<!-- cognis:install:end -->

## Quick start

```bash
pip install "git+https://github.com/cognis-digital/forkfuzz.git"
forkfuzz --version
forkfuzz scan .                       # scan current project
forkfuzz scan . --format json         # machine-readable
forkfuzz scan . --fail-on high        # CI gate (non-zero exit)
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="example"></a>
## Example

```text
$ forkfuzz scan .
  [HIGH    ] FOR-001  example finding             (./src/app.py)
  [MEDIUM  ] FOR-002  another signal              (./config.yaml)

  2 findings · risk score 5 · 38ms
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="architecture"></a>
## Architecture

```mermaid
flowchart LR
  A[Input: file / dir / API] --> B[Collectors]
  B --> C[Rules / Analyzers]
  C --> D[Scorer]
  D --> E{Reporters}
  E --> F[Table]
  E --> G[JSON / SARIF]
  E --> H[MCP tool -. drives .-> AI agents]
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="ai-stack"></a>
## Use it from any AI stack

`forkfuzz` is interoperable with every popular way of using AI:

- **MCP server** — `forkfuzz mcp` (Claude Desktop, Cursor, Cognis.Studio, [uncensored-fleet](https://github.com/cognis-digital/uncensored-fleet))
- **OpenAI-compatible / JSON** — pipe `forkfuzz scan . --format json` into any agent or LLM
- **LangChain · CrewAI · AutoGen · LlamaIndex** — wrap the CLI/JSON as a tool in one line
- **CI / scripts** — exit codes + SARIF for non-AI pipelines

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="how-it-compares"></a>
## How it compares

| | **Cognis forkfuzz** | Foundry (forge) invariant testing |
|---|:---:|:---:|
| Self-hostable, no account | ✅ | varies |
| Single command, zero config | ✅ | ⚠️ |
| JSON + SARIF for CI | ✅ | varies |
| MCP-native (AI agents) | ✅ | ❌ |
| Polyglot ports (JS/Go/Rust) | ✅ | ❌ |
| Open license | ✅ COCL | varies |

*Built in the spirit of **Foundry (forge) invariant testing / Echidna**, re-framed the Cognis way. Missing a credit? Open a PR.*

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="integrations"></a>
## Integrations

Pipes into your stack: **SARIF** for code-scanning, **JSON** for anything, an **MCP server** (`forkfuzz mcp`) for AI agents, and a webhook forwarder for SIEM/Slack/Jira. See [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="install-anywhere"></a>
## Install — every way, every platform

```bash
pip install "git+https://github.com/cognis-digital/forkfuzz.git"    # pip (works today)
pipx install "git+https://github.com/cognis-digital/forkfuzz.git"   # isolated CLI
uv tool install "git+https://github.com/cognis-digital/forkfuzz.git" # uv
pip install cognis-forkfuzz                                          # PyPI (when published)
docker run --rm ghcr.io/cognis-digital/forkfuzz:latest --help        # Docker
brew install cognis-digital/tap/forkfuzz                             # Homebrew tap
curl -fsSL https://raw.githubusercontent.com/cognis-digital/forkfuzz/main/install.sh | sh
```

| Linux | macOS | Windows | Docker | Cloud |
|---|---|---|---|---|
| `scripts/setup-linux.sh` | `scripts/setup-macos.sh` | `scripts/setup-windows.ps1` | `docker run ghcr.io/cognis-digital/forkfuzz` | [DEPLOY.md](docs/DEPLOY.md) (AWS/Azure/GCP/k8s) |

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="related"></a>
## Related Cognis tools

- [`reentryx`](https://github.com/cognis-digital/reentryx) — Static + symbolic detector that flags reentrancy, cross-function, and read-only reentrancy paths in Solidity/Vyper with CI-gating SARIF output.
- [`approvewarden`](https://github.com/cognis-digital/approvewarden) — Scans any wallet for dangerous ERC-20/721/1155 token approvals and infinite allowances, scoring drainer exposure and emitting revoke transactions.
- [`mevscope`](https://github.com/cognis-digital/mevscope) — Replays a tx or address history to attribute sandwich, frontrun, and backrun MEV extraction with per-trade loss accounting.
- [`rugradar`](https://github.com/cognis-digital/rugradar) — Token contract risk scanner detecting honeypots, hidden mint/blacklist functions, owner backdoors, and unlocked liquidity before you ape.
- [`storagelens`](https://github.com/cognis-digital/storagelens) — Diffs and decodes contract storage layouts across proxy upgrades to catch storage-collision and uninitialized-slot bugs.
- [`sigsleuth`](https://github.com/cognis-digital/sigsleuth) — Decodes raw calldata and EIP-712 typed-data into human-readable intent, flagging blind-signing and malicious permit/Permit2 payloads.

**Explore the suite →** [🗂️ all 170+ tools](https://github.com/cognis-digital/cognis-neural-suite) · [⭐ awesome-cognis](https://github.com/cognis-digital/awesome-cognis) · [🔗 cognis-sources](https://github.com/cognis-digital/cognis-sources) · [🤖 uncensored-fleet](https://github.com/cognis-digital/uncensored-fleet) · [🧠 engram](https://github.com/cognis-digital/engram)

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="contributing"></a>
## Contributing

PRs, new rules, and demo scenarios are welcome under the collaboration-pull model — see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

> ### ⭐ If `forkfuzz` saved you time, **star it** — it genuinely helps others find it.

## License

Source-available under the **Cognis Open Collaboration License (COCL) v1.0** — free for personal, internal-evaluation, research, and educational use; **commercial / production use requires a license** (licensing@cognis.digital). See [LICENSE](LICENSE).

---

<div align="center"><sub><b><a href="https://cognis.digital">Cognis Digital</a></b> · one of 170+ tools in the <a href="https://github.com/cognis-digital/cognis-neural-suite">Cognis Neural Suite</a> · <i>Making Tomorrow Better Today</i></sub></div>
