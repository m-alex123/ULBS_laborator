# Patterns — ULBS_laborator

<!-- graffino-agentic:begin v1 -->
> How we build things here. Copy only `approved` entries. `candidate` = seen once or
> not yet confirmed; agents add these freely. Promotion needs the user's OK.
<!-- graffino-agentic:end -->

## Index
- PATTERN-001 · SQLite Foreign Keys Enforcement & SQLAlchemy 2.0 Typed Declarative Models · candidate
- PATTERN-002 · Idempotent Database Seeding · candidate

---

## PATTERN-001 · SQLite Foreign Keys Enforcement & SQLAlchemy 2.0 Typed Declarative Models
- **Status:** candidate
- **Confirmed:** 2026-11-19
- **How:** In SQLite with SQLAlchemy 2.0, enforce referential integrity and cascading deletes by registering an engine connection listener for `PRAGMA foreign_keys=ON`, and declare all models using `class Base(DeclarativeBase)` with typed `Mapped[...]` and `mapped_column(...)`.
- **Example:**
```python
from sqlalchemy import Engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

## PATTERN-002 · Idempotent Database Seeding
- **Status:** candidate
- **Confirmed:** 2026-11-19
- **How:** Ensure database seed functions check for the existence of records by natural/unique keys (such as email, unique store identifier, or SKU) before inserting new rows, updating or skipping existing rows so that repeated runs of the seed script succeed deterministically without violating unique constraints.
- **Example:**
```python
def seed_site_configs(session):
    for store, defaults in STORE_DEFAULTS.items():
        existing = session.query(SiteConfig).filter_by(store=store).first()
        if not existing:
            session.add(SiteConfig(store=store, **defaults))
    session.commit()
```
