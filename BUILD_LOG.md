# BUILD LOG

## Nov 4
- Read Switch docs + cloned source for protocol details. Confirmed: file attachments delivered to agent as local paths; `send_attachment` posts images to Mattermost. Architecture in PLAN.md.
- Env: Python 3.13, Docker 29.8 present. `claude` CLI not on PATH in this shell (check in Console).
- Created venv, pinned deps: pandas 3.1.0, numpy 2.5.4, matplotlib 3.11.2, pytest 9.2.0.
- Built + tested core: config, loader (validation, encoding/sep sniffing, friendly errors), profile, charts (4 PNGs), ops (breakdown, IQR outliers, drivers), report, CLI (JSON output, thread-based timeout, server-side logging).
- Tests: 46 passed (unit + subprocess CLI integration, incl. bad file, oversize, timeout, hidden stack trace).
- Wrote agent/INSTRUCTIONS.md (playbook for the Switch agent).
- Next: human installs Switch Console, starts local server, creates `chateda` agent in this repo dir with INSTRUCTIONS.md, joins Mattermost room; hello round-trip, then live E2E.
- Blocker (human-only): Console is a GUI install.
