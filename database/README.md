The initial schema is defined in `backend/app/models.py` and exported to `schema.sql`.
Run `python -m backend.manage init-db` to create tables and initial system configuration.
This version has a single initial schema; future schema changes should use explicit migrations.
Run `python -m scripts.export_schema` to regenerate the PostgreSQL DDL.
Datasets are never stored in PostgreSQL. Upload records contain only ownership, parsing options, and expiry metadata.
