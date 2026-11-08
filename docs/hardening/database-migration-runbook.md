# Database migration runbook

## Before deployment

1. Stop application writes or use a reviewed maintenance window.
2. Take a database backup and confirm it can be read. See [backup and restore](backup-restore-runbook.md).
3. Supply `DATABASE_URL` from the deployment secret store. Production must use PostgreSQL.
4. Verify `DEMO_MODE=false`, a unique `JWT_SECRET` of at least 32 characters, explicit `ALLOWED_ORIGINS`, and `CHECKOUT_MERCHANT_ID`.
5. Keep `ENABLE_URL_INGESTION=false` until a qualified SSRF review is complete.

## Apply migrations

From the repository root in a Python environment with requirements installed:

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://USER:PASSWORD@HOST:5432/DATABASE"
$env:DEMO_MODE = "false"
Push-Location backend
alembic current
alembic upgrade head
alembic current
Pop-Location
```

Use the deployment platform's secret interpolation instead of literal credentials in shared terminal history. Verify the reported head is `8e6f27fd41bb`. The API refuses production startup when the migration version is missing or behind.

The first non-empty revision creates the current model schema while safely adopting tables from the earlier `create_all()` startup path. Follow-up revisions add checkout idempotency, shared login throttling, and anomaly-history fields. The original empty revision is retained; published history is not rewritten.

## Upgrade verification

Before applying to production, test the upgrade on a restored copy. Record key counts before and after, including `payment_transactions`, `payment_orders`, `payment_events`, `payment_ingestion_runs`, `alerts`, `anomalies`, `approvals`, and `audit_logs`. Compare checksums or business totals where relevant. Stop if any migration fails or counts unexpectedly change.

This branch verified fresh and prior-schema SQLite upgrades, including a legacy database copy with 50,004 payments retained. PostgreSQL migration tests were not run because Docker/psql were unavailable here. Do not treat the SQLite result as PostgreSQL proof.

## Rollback

Automated destructive Alembic downgrades intentionally raise an error to protect payment and audit history. Roll back the application image only if it remains compatible with the migrated schema. Otherwise restore the verified backup into a separate database and point the prior release at that restored copy. For schema changes, create a forward repair migration reviewed against a backup; never delete payment, event, decision, or audit rows to make a release pass.
