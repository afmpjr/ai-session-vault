# ai-session-vault

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
asv commit -m "message"        commit pending changes
asv log                        browse the vault history
asv show SESSION_ID            render a session as readable text
asv find QUERY                 search stored sessions
asv secrets scan/redact        detect and redact secrets before publishing
```

## Why

- Sessions are ephemeral: runtimes overwrite their JSONL files without
  warning. `asv` snapshots each change and keeps full history in git.
- Sessions are hard to find: a vault is a searchable, grep-able store.
- Sessions are hard to share safely: `asv` redacts secrets into reversible
  `[REDACTED:sha]` placeholders before anything is committed or published.
- No server, no daemon, no account, no lock-in: a vault is just a git
  repository with JSONL files.

## Install

```bash
./scripts/setup.sh        # creates .venv, installs the package (editable)
source .venv/bin/activate
asv --help
```

Requires Python 3.12+. There are no runtime dependencies beyond the standard
library and a system `git`.

## Documentation

- [`docs/01_usage.md`](docs/01_usage.md) — full usage guide.
- [`AI_HANDOFF.md`](AI_HANDOFF.md) — operational continuity notes (agent
  handoff).

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
  shapes; malformed lines are skipped, never fatal.
- **Secrets by default** — redaction is deterministic and reversible for the
  vault owner.

## License

MIT