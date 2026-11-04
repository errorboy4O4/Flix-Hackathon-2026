# ChatEDA — turn any team chat into a data team

**Track 01: Best Business Workflow** · Flip the Switch Hackathon (WeMakeDevs × DevTools Academy × Switch)

Drop a CSV into a team chat room. A Claude Code agent, connected to the room by **Switch**, profiles the data, posts a plain-language summary plus charts, and keeps iterating with the team in the thread: *"break monthly charges down by region"*, *"drop the outliers and redo"*, *"what drives churn?"*. No notebooks, no waiting on the data team.

> Demo video: **TODO: add link before submission**

## The problem

Every data-adjacent team lives in chat and waits on someone to open a notebook. Questions arrive in threads; answers arrive days later, detached from the conversation that asked for them.

## What it does

1. A teammate attaches a CSV in Mattermost and writes `@chateda analyze this`.
2. The agent returns shape, column types, missing values, key statistics, correlations, auto-generated insights and **4 chart images**.
3. Teammates ask follow-ups in the thread. The agent re-runs real analysis each time:

| Ask in chat | What runs |
|---|---|
| "break monthly_charges down by region" | `chateda breakdown --by region --metric monthly_charges` |
| "drop the outliers and redo the charts" | `chateda analyze --drop-outliers` |
| "what drives churn?" | `chateda drivers --target churn` |
| any of the above "without the outliers" | add `--drop-outliers` |

A real example from the sample data: the region breakdown showed North averaging 70.85 vs West 49.62. One thread message later ("without the outliers") the gap was about 2 points: six extreme rows had been inflating North. That is the workflow: question, answer, challenge, better answer, all in one thread.

**Guardrails.** Non-CSV, empty, header-only, binary, malformed and oversize files (25 MB / 500k rows by default) get a friendly explanation in chat instead of a stack trace. Runs are time-limited (120 s). Unknown column names get "did you mean" suggestions. Every error is logged server-side to `logs/chateda.log`.

## How Switch is used

**ChatEDA is impossible without Switch: the agent-to-chat bridge is the product.** This repo contains no chat bot, webhook server or Mattermost client. Switch provides all of it:

- **Switch Console** runs a local Switch server (Docker) with **Mattermost** bundled, and runs **Claude Code** as a room agent named `chateda`.
- **Inbound:** when a teammate attaches a CSV and mentions `@chateda`, Switch relays the message to Claude Code with the file **already downloaded to a local path**.
- **Outbound:** Claude Code replies with Switch's `post_message` tool and posts the charts with `send_attachment`, which Switch's Mattermost bridge turns into real file uploads in the same thread.
- **Roles and safety:** Switch handles `@` addressing (the agent ignores unaddressed chatter), threads, and approval prompts for commands the agent wants to run.

What we add on top is deliberately small and testable: a deterministic analysis toolkit (`chateda/`) and a playbook (`agent/INSTRUCTIONS.md`, loaded via `CLAUDE.md`) that tells the agent which command to run for which request and how to talk to non-engineers. All numbers in chat come from the toolkit's output, not from the model's imagination.

## Architecture

```
Teammate (Mattermost) ── CSV + "@chateda ..." ──▶ Switch server ──▶ Switch Console ──▶ Claude Code
                                                                                          │ runs
                                                                                          ▼
                                                                            python -m chateda <command>
                                                                            (pandas / matplotlib, tested)
                                                                                          │
                          Mattermost thread ◀── post_message + send_attachment ◀── JSON {message, charts}
```

| Path | Role |
|---|---|
| `chateda/loader.py` | validate and load CSVs, friendly errors |
| `chateda/profile.py` | shape, types, missing values, stats, correlations, insights |
| `chateda/charts.py` | PNG charts (matplotlib, headless) |
| `chateda/ops.py` | breakdowns, IQR outliers, driver ranking |
| `chateda/report.py` | markdown for chat |
| `chateda/cli.py` | command line entry point, timeout, logging; always prints one JSON object |
| `agent/INSTRUCTIONS.md` | the agent's playbook (`CLAUDE.md` imports it) |
| `fixtures/sample.csv` | 600-row customer-churn sample with injected outliers and missing values |
| `tests/` | unit tests plus subprocess integration tests of the CLI |

## Setup and reproduce

Requirements: Python 3.11+, Docker Desktop, Node.js (only if Switch Console's built-in Claude Code installer fails), and a Claude subscription or API key.

**1. Toolkit and tests**

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # macOS/Linux: .venv/bin/pip
.venv/Scripts/python -m pytest                    # 47 tests
.venv/Scripts/python -m chateda analyze fixtures/sample.csv
```

Optional configuration: copy `.env.example` to `.env` and export the `CHATEDA_*` variables (file size, row cap, timeout, output folder) in the environment that launches the agent. Defaults work out of the box.

**2. Switch + agent**

1. Install **Switch Console** (<https://docs.switchagents.ai/switch-rooms/getting-started/install-switch-console>), choose **On this computer**, and press **Start** on the local server. Keep Docker Desktop and Console open while you use it.
2. In **Settings > Agent providers**, make sure **Claude Code** is signed in (`claude auth login`). If Console's installer fails on Windows: `npm install -g @anthropic-ai/claude-code`, then restart Console.
3. **Your Agents > New agent:** name `chateda`, run location *This computer*, **Directory = this repository's root**, provider *Claude Code*. Leave instructions empty: `CLAUDE.md` supplies them.
4. **Add to room:** pick **Town Square** (bundled Mattermost) or any room.
5. Open Mattermost from Console (**Home > Mattermost > Sign-in details… > Open in Mattermost**), attach `fixtures/sample.csv` and send `@chateda analyze this`.

## Tests

`pytest` runs 47 tests: CSV validation edge cases, profiling, chart PNG validity, follow-up operations, and the CLI end to end in a subprocess (bad files, size limits from environment, timeout, unexpected exceptions never leaking internals).

## Limitations

- Local agents answer only while Switch Console is running.
- Local Switch servers admit one user, so the demo is a person plus the agent; connecting Slack or Discord would add teammates.
- Outlier handling uses the 1.5×IQR rule; driver ranking is association strength (correlation, correlation ratio, Cramér's V), not a trained model, and the agent says so in every reply.
