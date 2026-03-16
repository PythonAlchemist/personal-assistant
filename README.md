# Personal Family Assistant

A CLI-based personal and family life organizer. Manages schedules, tasks, email, directions, and daily briefings from the terminal.

## Tech Stack

- **Python 3.13** with Click CLI framework
- **SQLite** for local storage (family data)
- **Todoist** for task management (via MCP + REST API)
- **Google APIs** — Calendar, Gmail, Maps
- **Open-Meteo** — weather (free, no key)
- **Anthropic SDK** — chat mode (Claude)
- **Rich** — terminal formatting
- **uv** — package management

## Project Structure

```
src/assistant/
  cli/        Click command groups
    main.py       CLI entrypoint
    briefing.py   Daily briefing renderer
    calendar.py   Google Calendar commands
    chat.py       AI chat mode
    family.py     Family data commands
    gmail.py      Gmail commands
    maps.py       Google Maps commands
    todo.py       Local todo commands (legacy)
  models/     Dataclasses
    family.py     Family member model
    todo.py       Todo model (legacy)
  storage/    SQLite layer
    database.py     Connection + schema init
    family_repo.py  Family CRUD
    todo_repo.py    Todo CRUD (legacy)
  services/   Business logic
    briefing.py     Daily briefing aggregator
    calendar.py     Google Calendar operations
    family.py       Family data operations
    gmail.py        Gmail operations
    google_auth.py  OAuth2 multi-account auth
    maps.py         Google Maps operations
    todo.py         Local todo operations (legacy)
    weather.py      Open-Meteo weather
  config.py   Paths, env vars, account aliases
data/
  .env              API keys (gitignored)
  assistant.db      SQLite database (gitignored)
  tokens/           Google OAuth tokens (gitignored)
```

## Setup

```bash
# Install dependencies
uv pip install -e .

# With chat support
uv pip install -e '.[chat]'

# Configure API keys in data/.env
GOOGLE_MAPS_API_KEY=...
TODOIST_API_TOKEN=...
# ANTHROPIC_API_KEY loaded from environment or .env
```

Google OAuth credentials go in `data/google_credentials.json`. Tokens are cached per-account in `data/tokens/`.

## Google Accounts

Two accounts are configured with Calendar + Gmail scopes:

| Alias | Email | Use |
|-------|-------|-----|
| `personal` | christopher.singer.analytics@gmail.com | Primary |
| `crossfit` | csinger1.crossfit@gmail.com | Personal/family |

## Usage

```bash
# Daily briefing (weather, calendar, todos, email summary)
assistant briefing

# Calendar
assistant calendar today
assistant calendar week

# Gmail
assistant gmail unread
assistant gmail inbox

# Maps
assistant maps directions "Home" "Work"
assistant maps nearby "restaurants"

# Family
assistant family list
assistant family birthdays

# Chat
assistant chat
```

## Todoist Integration

Todoist is the primary task management system. Tasks are captured quickly via the Todoist mobile app, then triaged and enriched through AI-assisted sessions in Claude Code using the Todoist MCP server.

### Workflow

1. **Capture** — Quick-add tasks from the Todoist mobile app throughout the day. Keep it light: just a title is fine.
2. **Triage** — In a Claude Code session, review inbox items conversationally. AI suggests priorities, descriptions, labels, and due dates. You approve or adjust, then AI writes updates back to Todoist via MCP.
3. **Weekly rotation** — Each triage session, review and rotate the `This_Week` label to reflect current intent.
4. **Briefing** — The daily briefing pulls active tasks from Todoist to show what's due and what's planned.

### Task Organization

**Due dates mean real deadlines only.** If missing a date has consequences (bills, appointments, expiring offers), it gets a due date. Everything else is undated.

**Labels drive intent and categorization:**

| Label | Purpose |
|-------|---------|
| `This_Week` | Tasks you intend to work on this week. Rotated during triage. |
| `Waiting` | You've taken action, ball is in someone else's court. |
| `Home_Chores` | Household tasks and maintenance |
| `Home_Improvement_Projects` | Larger home projects |
| `Health` | Medical, dental, wellness |
| `Wealth` | Financial tasks — insurance, bills, budgeting |
| `Tech` | Technology research and projects |
| `Growth` | Personal development |
| `Build` | Building/making projects |
| `Recurring` | Paired with recurring due dates (e.g., air filters every 6 months) |

**Priority levels** (Todoist numbering):

| Todoist Priority | Meaning |
|-----------------|---------|
| p1 (urgent) | Must do ASAP, blocking something |
| p2 (high) | Important, do this week |
| p3 (medium) | Should do soon, not urgent |
| p4 (normal) | Backlog, get to it eventually |

**Everything stays in Inbox.** No need for multiple projects at current task volume. Sections and boards are unnecessary overhead.

### MCP Configuration

The Todoist MCP server is configured in `.mcp.json` for Claude Code sessions. It provides full CRUD access to tasks, projects, labels, sections, and comments.

### Legacy Local Todos

The SQLite-based todo system (`cli/todo.py`, `services/todo.py`, `storage/todo_repo.py`) is legacy. Todoist replaces it. These modules remain in the codebase but are not actively used.

## Daily Briefing

The briefing aggregates data from multiple services into a morning overview:

- **Weather** — Today's forecast (Open-Meteo, Harrisburg NC)
- **Calendar** — Today's events + week overview (both Google accounts)
- **Todos** — Active Todoist tasks: overdue, due soon, this week's plan
- **Email** — Unread count per account
- **Family** — Upcoming birthdays

## Configuration

All configuration lives in `src/assistant/config.py`:

- Paths resolve relative to project root
- API keys load from `data/.env` (with `os.environ` fallback)
- Google account aliases map to email addresses
- Weather coordinates hardcoded to Harrisburg, NC (35.2271, -80.6490)
- Timezone: America/New_York
