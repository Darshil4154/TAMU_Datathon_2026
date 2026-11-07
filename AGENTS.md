# Team Agent Rules

Every coding agent on this team reads this file (Codex reads AGENTS.md automatically; for Claude Code, keep a copy named CLAUDE.md).

## Project
<One or two lines: what we're building, the stack, how to run it locally.>

## Folder ownership (strict)
Each person's agent may ONLY create or edit files inside its owner's folders.

| Owner (GitHub username) | Owns | Responsibility |
|---|---|---|
| @Darshil4154 | /frontend | UI, pages, components |
| @teammate2 | /backend | API routes, database |
| @teammate3 | /ml | model, prompts, inference |
| @teammate4 | /infra, /docs | deploy, README, demo script |

Shared files (package.json, .env.example, root config): only the /infra owner edits them. Everyone else asks on the board.

If your task needs a change outside your folders: do NOT make it. Post on the board, tag the owner, and say exactly what you need.

## Contracts between parts
- API base URL: <...>
- Endpoint shapes live in /docs/api.md. The owner of an endpoint updates this file when it changes and tags whoever uses it.

## Message board
- The board is pinned issue #1. That is the only place agents talk to each other.
- Post when you finish something someone depends on, or when you are blocked.
- Format: what you did, files/endpoints changed, then tag the people you need with exactly what you need.
- Never tag someone just to acknowledge or say thanks. No tag = no reply needed.

## Git
- Agents do NOT run git commit or git push. The board script commits and pushes after each task.
- Never edit or revert another owner's files.
