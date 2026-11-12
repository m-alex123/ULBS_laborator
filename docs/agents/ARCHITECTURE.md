# Architecture — ULBS_laborator

<!-- graffino-agentic:begin v1 -->
> How this repo is built, generated from the code at backfill and kept current by
> whoever changes the structure. The code wins: when this page is wrong, fix it.
<!-- graffino-agentic:end -->

## Overview
Repository for ULBS laboratory assignments and projects. Currently in initial setup phase awaiting coursework instructions and stack selection.

```text
[Repository Root]
  ├── docs/agents/      (Agent documentation, decisions, patterns, contracts)
  └── .claude/          (Skills and agent definitions)
```

## Parts
| Part | Path | Responsibility | Talks to |
|---|---|---|---|
| Documentation | docs/agents | Project governance, patterns, and architectural records | Developers, Agents |

## Data flow
1. Laboratory assignment requirements provided by instructor.
2. Architecture and stack established via `/plan`.
3. Solution implemented and verified via `/build`.

## State and storage
| What | Where | Owner | Notes |
|---|---|---|---|
| Source code & docs | Git repository | Author / Student | Tracked in main branch |

## Configuration
| Name | Where set | Used by | Notes |
|---|---|---|---|
<!-- names only, never values -->

## Build, deploy, runtime
Build and execution commands to be defined once the laboratory stack is established (see AGENTS.md section 2).

## Boundaries
Local repository development and academic assignment grading boundaries.
