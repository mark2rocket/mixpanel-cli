# mixpanel-cli

Agent-native Mixpanel CLI — JSON output, REPL mode, AI-powered analytics.

## Install

```bash
pip install mixpanel-cli          # Phase 1 (core CLI)
pip install mixpanel-cli[ai]      # + AI natural language queries
pip install mixpanel-cli[all]     # everything
```

## Quick Start

```bash
mixpanel config init
mixpanel analytics insight --event "Sign Up" --from-date 2026-03-01 --to-date 2026-03-26
```

See [SKILL.md](SKILL.md) for agent usage patterns.
