# PLAN — ChatEDA (Flip the Switch Hackathon, Track 01: Best Business Workflow)

## Verified facts about Switch (from docs + source, 2026-11-04)

- Switch Console (desktop app) runs a local Switch server in Docker, which **bundles Mattermost**.
- Console runs **Claude Code** as a room agent. Addressed with `@agent-name`; ignores unaddressed messages.
- Uploaded files arrive **already downloaded to local paths** in the agent's message (any type, incl. CSV). Cap 20 MB default, server-configurable.
- Agent tools: `post_message`, `send_attachment(path|paths, caption, thread_id)`, `download_attachment(mxc)`, `read_context`. Attachments land as real Mattermost uploads. Threads supported.
- The agent works in a configured **directory** and follows its **agent instructions**. Agents on "This computer" only answer while Console runs.

## Architecture

```
Teammate (Mattermost) --CSV + @chateda--> Switch server --> Switch Console --> Claude Code
                                                                      |  runs
                                                                      v
                                                          python -m chateda <cmd>   (this repo)
                                                                      |
                                    summary.md + chart PNGs  <--------+
                                                                      |
Claude Code: post_message(summary) + send_attachment(charts) --> Switch --> Mattermost thread
```

Switch is the bridge; this repo is the **analysis toolkit + agent playbook**:

- `chateda/` Python package, deterministic and fully tested. The agent calls it through a CLI, so analysis is reproducible and not LLM-hallucinated.
- `agent/INSTRUCTIONS.md` — the playbook pasted into the Switch agent: how to find the CSV path, which command to run for which request, how to reply in plain language, how to report errors.
- `fixtures/` sample CSVs.

## Components

| Module | Job |
|---|---|
| `config.py` | env-driven limits (`CHATEDA_MAX_MB`, `CHATEDA_MAX_ROWS`, `CHATEDA_TIMEOUT_S`, `CHATEDA_OUT_DIR`) |
| `loader.py` | validate + load CSV; friendly `ChatEdaError(user_message)` |
| `profile.py` | shape, dtypes, missing, describe, correlations, insights |
| `charts.py` | 3–4 PNG charts (matplotlib Agg) |
| `ops.py` | follow-ups: `breakdown`, `outliers` (drop + redo), `drivers` (what predicts column X) |
| `report.py` | markdown summary |
| `cli.py` | `analyze`, `breakdown`, `outliers`, `drivers`; JSON result with file paths; timeout; friendly errors, logs to stderr/file |

## Task breakdown

1. [x] Read docs/source, confirm attachment path (Nov 4)
2. [ ] Scaffold repo (.gitignore, .env.example, requirements, fixtures)
3. [ ] loader + tests -> profile + tests -> charts + tests -> report + tests
4. [ ] ops (breakdown/outliers/drivers) + tests
5. [ ] CLI + timeout + integration test (CLI end-to-end on fixture)
6. [ ] Human step: install Switch Console, start local server, create agent with `agent/INSTRUCTIONS.md`, confirm hello round-trip
7. [ ] Live E2E in Mattermost, fix gaps
8. [ ] README, demo script, video, review walkthrough, submit by Nov 7 18:00 IST

## Risks / cuts

- Claude CLI not found in this shell PATH; Console's Agent providers screen will tell us. Human must run `claude auth login` if needed.
- Console is a GUI install: human-only step. Everything else is built and tested without it.
- Discord stretch: cut unless done early.
