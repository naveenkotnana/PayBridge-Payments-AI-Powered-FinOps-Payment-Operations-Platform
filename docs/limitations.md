# Limitations

Stated plainly. Nothing here is hidden in a footnote.

## Evaluated & Measured

**Local LLM execution.** OpsPilot operates 100% locally with zero external API calls. When an Ollama instance is present with `qwen2.5:3b-instruct`, live generative inference powers the root-cause narrative. When Ollama is offline, the deterministic rule-based fallback immediately engages without raising exceptions. Both branches are covered in test suites and CI gates.

**Anomaly precision/recall.** The dataset contains one intentional duplicate usage row and six April exceptions, correctly surfaced. That is a targeted operational ground truth rather than a multi-thousand injected benchmark, so speculative precision or recall metrics are not claimed.

## Design Trade-offs

**TF-IDF is lexical.** Measured Recall@4 = 1.000 on this policy corpus, partly because the evaluation queries align with policy terminology. For broader user phrasing divergence, `EMBEDDING_MODE=ollama` enables dense local embeddings via `nomic-embed-text`.

**Fixed investigation plan.** The state machine planner currently runs three focused investigation queries for every revenue alert. While correct and robust for this alert taxonomy, dynamic query selection based on alert category remains an extension area.

**Location-month grain alerting.** Anomaly detection aggregates at location-month grain because root causes in physical meter operations are site-scoped. Apartment-level outliers are surfaced through analytical SQL (`revenue_outliers`) but do not trigger independent system alerts.

## Implementation Status

**Database Migrations.** Alembic is fully configured (`alembic.ini`, `alembic/env.py`) with baseline revision `3288d1cab678_initial_schema.py` tracking all 13 domain tables.

**Customer Config.** Customer configuration loader (`config/customers.yaml` + `app/core/customer_config.py`) is implemented with unit tests covering tool whitelisting, approval rules, and role permissions.

**SQL Guardrails.** Allowlisted queries, forbidden keyword regexes, single-statement enforcement, and hard row limits are enforced at the tool layer. SQLite driver-level execution cancellation for `SQL_TIMEOUT_S` is not natively enforced.

**Observability.** Structured JSON logs with context-propagated `trace_id` and `workflow_id`, along with a dedicated `/metrics` REST endpoint. For production microservices, an external collector (e.g. Prometheus / OpenTelemetry) would be recommended.

## Security Scope

Includes JWT authentication, role-based authorization (RBAC: Analyst, Manager, Admin), prompt injection pattern stripping, and SHA-256 idempotency keying. Rate limiting and refresh-token rotation are omitted in this local prototype environment. All telemetry, entities, and credentials are synthetic.
