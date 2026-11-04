# Demo video script (target 2:30, hard cap 3:00)

Record the Mattermost window with Switch Console visible once. Keep Console, Docker Desktop and the `chateda` agent running. Pre-warm the agent with one throwaway message so the first reply isn't slow. Use `fixtures/sample.csv`.

| Time | On screen | Say |
|---|---|---|
| 0:00 | Title card or Town Square | "Data questions live in team chat but get answered in notebooks, days later. ChatEDA puts the analyst in the chat." |
| 0:15 | Switch Console: agent `chateda`, Claude Code, Running, local server | "This is Switch. It connects Claude Code to Mattermost. There is no bot code in my repo: Switch is the bridge, and without it this project does not work." |
| 0:35 | Attach sample.csv, send `@chateda analyze this` | "I drop a CSV and tag the agent. Switch hands the file to Claude Code." |
| 0:50 | Summary and 4 charts appear | "Back comes a plain-language summary and four charts, uploaded by Switch as real files. Note monthly charges is skewed and total charges has a negative value." |
| 1:15 | `@chateda break monthly_charges down by region` | "Now the team iterates. North looks 43% higher than West." |
| 1:35 | `@chateda without the outliers` (same thread) | "Someone challenges it: is that real?" |
| 1:50 | Reply shows gap collapsed to ~2 points | "Six extreme rows were inflating North. Question, answer, challenge, better answer, all in one thread." |
| 2:10 | `@chateda what drives churn?` | "And a quick driver ranking, with the honest caveat: association, not cause." |
| 2:25 | Attach `report.pdf`, reply shows friendly error | "Bad input gets a friendly message, never a stack trace." |
| 2:40 | Repo/README, `pytest` green | "47 tests, reproducible setup, built for Track 01. Thanks." |

Checklist before recording: Mattermost logged in, Town Square clean, browser zoom 110–125%, no personal info on screen, Console password never shown.
