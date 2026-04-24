# Summarizer-Role Feature

Python-side implementation of the Summarizer-Role rounds (Rounds 1–8,
2026-04-22/23). This document is the runtime and developer reference:
what files do what, which endpoints exist, and how to configure the
pieces that need keys or tuning.

## One-line overview

Every journal write auto-updates a three-tier YAML summary file and a
SQLite vector index. Agents can query the index for contextually
relevant chunks (RAG) or trigger a fresh summary on demand.

## Files

| Path | Purpose |
| --- | --- |
| [src/middleware/summary_store.py](../src/middleware/summary_store.py) | `TieredSummary` schema (full/compressed/shorthand) + YAML I/O. |
| [src/middleware/summary_meta.py](../src/middleware/summary_meta.py) | Post-commit hook, `last_entry_id`, threshold detection. |
| [src/middleware/summary_index.py](../src/middleware/summary_index.py) | SQLite `chunk_index` + CRUD. |
| [src/middleware/embedder.py](../src/middleware/embedder.py) | OpenAI embedder (text-embedding-3-small) + float32 packing. |
| [src/middleware/retrieval.py](../src/middleware/retrieval.py) | Cosine similarity with numpy; top-K RetrievalHit list. |
| [src/middleware/summary_generator.py](../src/middleware/summary_generator.py) | Claude Haiku tier generator + persistence orchestrator. |
| [src/middleware/fidelity_check.py](../src/middleware/fidelity_check.py) | Forge's Round 5 validation rules against live AICP fields. |
| [src/middleware/agent_config.py](../src/middleware/agent_config.py) | Loads `agent_config.json`; resolves API keys env-first. |
| [scripts/backfill_embeddings.py](../scripts/backfill_embeddings.py) | CLI utility for embedding pre-existing NULL-embedding rows. |

## Data layout

```
<repo>/
  agent_config.json              # summarizer role, fallback chain, provider/model, budgets
  summaries/
    index.db                     # single SQLite DB (project column isolates)
    <project>/
      summary.yml                # YAML with full/compressed/shorthand tiers + metadata
      summary_meta.json          # last_entry_id, entries_since_last_summary, last_updated
```

## HTTP endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`  | `/threads/{project}/summary-due` | Returns `{due, threshold, entries_since_last_summary, last_entry_id, last_updated}`. Optional `?threshold=N`. |
| `POST` | `/threads/{project}/retrieve` | Body `{query, top_k?}`. Returns `{count, hits: [{chunk_id, content, score, ...}]}`. |
| `POST` | `/threads/{project}/generate-summary` | Body `{limit?}`. Runs the Q4 generator end-to-end; writes `summary.yml`, advances `summary_meta`. 502 on LLM failure. |
| `GET`  | `/threads/{project}/rag-prefix` | Query params `?query=...&top_k=N`. Returns a pre-formatted `text/plain` prefix block for the Hub to splice into the agent prompt. Empty string (200) when no hits or empty query. |

Existing endpoints unchanged: `POST /threads/{project}/messages`,
`POST /threads/{project}/dispatch`, `GET /threads/{project}`, etc.

## Configuration (`agent_config.json`)

```json
{
  "summarizer_role": "Lumen",
  "summarizer_fallback_chain": ["Lodestar", "Pharos", "Forge"],
  "summary_generator": {
    "provider": "anthropic",
    "model": "claude-haiku-4-5-20251001",
    "max_input_tokens": 8192,
    "max_output_tokens": 2048,
    "tier_token_budgets": { "full": 2000, "compressed": 500, "shorthand": 100 }
  },
  "embedder": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "dims": 1536
  },
  "retrieval": { "top_k": 5 },
  "threshold": 5
}
```

## API keys (flexible installer path)

Keys are resolved by [`resolve_api_key`](../src/middleware/agent_config.py)
with a strict precedence:

1. **Environment variable** wins:
   - `ANTHROPIC_API_KEY` — Claude Haiku for Q4 summary generation.
   - `OPENAI_API_KEY` — text-embedding-3-small for chunk embeddings and retrieval queries.
2. **Fallback**: `anthropic_api_key` / `openai_api_key` fields in `agent_config.json` (not checked in by default — installer opts in at their own visibility risk).
3. **Neither present**: `MissingApiKey` raised with an error message naming both options.

The embedder hook in `api/server.py` swallows missing-key errors silently
and leaves `chunk_index.embedding` NULL for that row. Run
`scripts/backfill_embeddings.py` later to populate missing embeddings.

## Design decisions (locked across Rounds 1–8)

| # | Decision | Source |
| --- | --- | --- |
| Q1 | Single YAML-frontmatter `summary.yml` per project, three tiers. | Lumen Round 2/3 |
| Q2 | Post-commit hook on journal writes; per-project `summary_meta.json` counter; threshold default 5 (provisional). | Pharos Round 6 |
| Q3 | Fidelity check uses live AICP fields only: $DECISION enum, non-empty $TASK, $STATUS in expected set, payload-baseline comparison. | Forge Round 5 |
| Q4 | REVIEW/PLAN → project snapshot; RESPONSE → prompt-prefix; UPDATE → brainstorming consolidation. | Lodestar Round 6 |
| Q5 | RAG over prefix injection. Cosine similarity over text-embedding-3-small. Per-`$ID` chunk boundary. SQLite storage. Compressed tier default, full fallback, shorthand under size constraint. | Trident / Lumen / Pharos / Lodestar Round 7 |
| Q6 | Static `summarizer_fallback_chain` in `agent_config.json`. On dispatch failure, advance. Chain exhausted → raw-last-N. | Lumen Round 4 (accepted) |
| Q8 | Staleness detected numerically: `max(journal.$ID) > summary_meta.last_entry_id`. | Forge + Lumen Round 6 |

## Dependencies

Listed in [requirements.txt](../requirements.txt). New (since this feature):
`PyYAML`, `numpy`, `openai`, `anthropic`. FastAPI/uvicorn/pydantic were already in use.

## Smoke test

Start the API, then post a journal entry and confirm both the meta
counter and the index row grew:

```powershell
H:\Code\interai-protocol\Start-JournalAPI.ps1
H:\Code\PowerShell\Smoke Test.ps1
```

With `OPENAI_API_KEY` set, the resulting chunk row will have a populated
`embedding` blob; without it, the row lands with NULL and can be
backfilled later via `python scripts/backfill_embeddings.py`.

## What is NOT here (yet)

- **Sync-to-deploy.** The summaries/ directory is not currently replicated to the `aicp-journals` deploy repo. Journal writes are; summaries are local artifacts.

## What was delivered today beyond the original scope

- **Background scheduler** (`src/middleware/summary_scheduler.py`) — opt-in via `scheduler.enabled=true` in `agent_config.json`; default interval 300s. Calls `update_project_summary` on any project whose counter crossed the threshold.
- **Hub VB.NET RAG consumer** — `FetchRagContext` in `AgentHubPresenter.vb` calls `GET /threads/{project}/rag-prefix` once per dispatch and prepends the returned text block to the prompt. Lives in the `interai-hub` repo (commit 42664a2).
- **Backfill utility** (`scripts/backfill_embeddings.py`) — CLI that walks `chunk_index`, finds NULL embeddings, batches through the OpenAI API, writes the vectors back. Supports `--dry-run`, `--project`, `--batch`.
- **requirements.txt** at the repo root pinning the six runtime deps.
