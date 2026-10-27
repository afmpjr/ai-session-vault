# ai-session-vault

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-79%2F79%20passing-brightgreen.svg)](https://github.com/afmpjr/ai-session-vault/actions)

**~1.2 K sessions indexed across 4 runtimes • streaming search • auto-repack • local-first**

Local-first version control for AI agent sessions.

Agent runtime sessions (Claude Code, OpenCode, Codex, and others) are plain
JSONL files that get overwritten, compacted, and cleaned up at any moment.
`asv` puts git-backed snapshots and version history on top of them, so
"that conversation from last Wednesday that finally cracked the bug" becomes
something you can find, continue, and hand to a teammate — with nothing leaving
your machine.

```
asv init                       initialise a vault
asv add --runtime claude FILE  snapshot a session into the vault
asv sync                       discover, snapshot, and commit in one step
asv commit -m "message"        commit pending changes
asv log                        browse the vault history
asv status                     show vault location, sessions, dirty state, storage
asv show SESSION_ID            render a session as readable text
asv find QUERY                 search stored sessions, newest first (--limit N, --runtime R, --since 7d|ISO date)
asv discover                   list session files matching configured paths
asv config set paths.codex GLOB  override a runtime's session path glob
asv secrets scan FILE          detect secrets in a session file
asv secrets redact FILE        redact secrets with reversible placeholders
asv export SESSION_ID          export session metadata or transcript
asv repack                     force git repack of loose objects
```

## Why

- **Sessions are ephemeral**: runtimes overwrite their JSONL files without
  warning. `asv` snapshots each change and keeps full history in git.
- **Sessions are hard to find**: a vault is a searchable, grep-able store.
- **Sessions are hard to share safely**: run `asv secrets redact FILE --dict D`
  to replace secrets with reversible `[REDACTED:sha]` placeholders before
  anything is shared or pushed. Locally the vault keeps raw snapshots — private
  on your machine by default; redaction is the sharing gateway.
- **No server, no daemon, no account, no lock-in** — a vault is just a git
  repository with JSONL files.
- **Automatic packing (ADR-001)** — keeps history packed down to ~16× smaller
  without bloated loose objects.

## Install

```bash
# Global (recommended)
pipx install git+https://github.com/afmpjr/ai-session-vault.git

# Or with pip
pip install git+https://github.com/afmpjr/ai-session-vault.git

# Development (editable)
git clone https://github.com/afmpjr/ai-session-vault.git
cd ai-session-vault
./scripts/setup.sh        # creates .venv, installs the package (editable)
source .venv/bin/activate
asv --help
```

Requires Python 3.12+. There are no runtime dependencies beyond the standard
library and a system `git`.

## Usage at a glance

```bash
# Initialise a vault (git repo + config); built-in paths point at real
# runtimes:
# - Claude Code (~/.claude/projects/*/*.jsonl)
# - Codex (~/.codex/sessions/**/*.jsonl)
# - Antigravity (~/.gemini/antigravity/brain/*/.../transcript.jsonl)
# - OpenCode (~/.local/share/opencode/sessions/*.jsonl, auto-extracted from the
#   SQLite store; both the legacy session/message/part and the v2
#   session_v2/session_message schemas are supported)
asv init ~/.ai-session-vault

# Sync all sessions across all runtimes in one step (event-driven, no cron)
asv sync

# Or list the session files `asv add` can snapshot right now
asv discover

# Override where a runtime's sessions live (stored in vault.json, per vault)
asv config set paths.codex "~/.codex/archive/**/*.jsonl"

# Snapshot a session file; run from inside the vault dir or pass --vault
asv add --runtime claude ~/.claude/projects/<proj>/<session>.jsonl

# Commit pending changes to the vault's git history
asv commit -m "snapshot: fixed deploy script"

# Explore
asv log                    # recent commits
asv status                 # session counts + dirty state + storage health
asv find "retry logic"     # text search over stored sessions (streaming)
asv show <session-id>      # readable transcript
asv export <session-id>    # transcript or JSON metadata
asv export <session-id> --format json  # machine-readable
asv repack                 # force git repack (auto runs on commit if needed)
asv secrets scan FILE      # detect API keys, tokens, passwords
asv secrets redact FILE --dict ~/.asv-redaction.dict --output FILE.redacted
```

## Real-world example

```bash
$ asv status
vault:      /home/user/.ai-session-vault
sessions:   1184
runtimes:   antigravity, claude, codex, opencode
dirty:      no
storage:    164 loose objects (2736 KiB) [healthy]

$ asv find "security migration"
[
  {
    "session_id": "ses_ea81d0bb3ffe3JC4zqCY3Bp3ZK",
    "runtime": "opencode",
    "matches": 5,
    "snippets": [
      "migration corretiva ... REVOKE EXECUTE ... FROM anon, PUBLIC",
      "landlords vejam SÓ perfis com is_public = true"
    ]
  }
]

$ asv show ses_ea81d0bb3ffe3JC4zqCY3Bp3ZK
# Full readable transcript with turns, timestamps, tool calls
```

Full details in [`docs/01_usage.md`](docs/01_usage.md).

## Documentation

- [`docs/01_usage.md`](docs/01_usage.md) — full usage guide.
- [`docs/ADR-001-session-storage.md`](docs/ADR-001-session-storage.md) — storage architecture and packing strategy.
- [`AI_HANDOFF.md`](AI_HANDOFF.md) — operational continuity notes (agent handoff).

## Development

```bash
./scripts/test.sh          # run the full test suite (stdlib unittest)
./scripts/test.sh --verbose
```

The project follows TDD: tests live in `tests/` and cover the core modules
(session parsing, vault operations, transcripts, search, redaction, CLI).

## Design principles

- **Local-first** — all state lives on the machine; nothing is sent anywhere.
- **Open formats** — plain JSONL + JSON sidecars; git drives versioning.
- **No lock-in** — copy, tar, or `git push` a vault; there is no proprietary
  storage.
- **No daemon** — every operation is an explicit CLI action.
- **Tolerant parsing** — sessions from different runtimes have different JSON
  shapes (claude sends `sessionId` at the top level, codex nests it in
  `payload`); malformed lines are skipped, never fatal.
- **Configurable paths** — built-in session path globs are verified against
  real runtimes, and each vault can override them per runtime via
  `asv config set paths.<runtime> <glob>`.
- **Secrets by default** — redaction is deterministic and reversible for the
  vault owner.

## License

MIT

---

**Repository**: https://github.com/afmpjr/ai-session-vault  
**Issues & Discussions**: https://github.com/afmpjr/ai-session-vault/issues