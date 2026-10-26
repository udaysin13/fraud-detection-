# Database migrations

VaultGuard never drops or recreates tables during normal startup. Apply schema changes
explicitly before starting the API.

For a new empty SQLite or MySQL database, with `DATABASE_URL` configured:

```powershell
python -m alembic -c backend/alembic.ini upgrade head
```

For an existing VaultGuard database that already has the baseline tables, take a backup
first, inspect the schema, then mark it at the baseline and run the non-destructive
label-separation migration:

```powershell
python -m alembic -c backend/alembic.ini stamp 0001_baseline_schema
python -m alembic -c backend/alembic.ini upgrade head
```

Do not run `downgrade` against a populated database. MySQL passwords in `DATABASE_URL`
must be URL-encoded (`@` → `%40`, `:` → `%3A`, `/` → `%2F`).
