# Backup and restore runbook

These commands are templates. Run them from a protected operator environment with database credentials supplied through the secret manager, not committed in shell history or documentation.

## PostgreSQL logical backup

```bash
pg_dump --format=custom --no-owner --file="paybridge-$(date -u +%Y%m%dT%H%M%SZ).dump" "$DATABASE_URL"
```

Store the backup in an encrypted, access-controlled location. Record the database identifier, timestamp, application release, migration head, and backup checksum. Apply the organization's retention and access policy.

## Restore smoke test

Restore to a separate isolated database, never over the active database:

```bash
createdb --host="$RESTORE_HOST" --username="$RESTORE_USER" "$RESTORE_DATABASE"
pg_restore --host="$RESTORE_HOST" --username="$RESTORE_USER" --dbname="$RESTORE_DATABASE" --no-owner --exit-on-error "$BACKUP_FILE"
psql --host="$RESTORE_HOST" --username="$RESTORE_USER" --dbname="$RESTORE_DATABASE" -v ON_ERROR_STOP=1 -c "SELECT version_num FROM alembic_version;"
psql --host="$RESTORE_HOST" --username="$RESTORE_USER" --dbname="$RESTORE_DATABASE" -v ON_ERROR_STOP=1 -c "SELECT count(*) FROM payment_transactions;"
```

Compare the restored row counts and business totals with the backup record. Run a read-only application smoke check against the restored copy before declaring recovery successful.

## Local SQLite demo backup

Do not copy a live SQLite database using a plain file copy while writes are active. Stop the application and use SQLite's online backup API or the `sqlite3 .backup` command. Restore to a new file, open it read-only first, and verify key tables before pointing the demo at it.

## Evidence and current limitation

No PostgreSQL backup/restore smoke test was executed for this branch because Docker and PostgreSQL client utilities are unavailable in the environment. The existence of this runbook is not proof that a backup schedule or recovery-time objective is configured.
