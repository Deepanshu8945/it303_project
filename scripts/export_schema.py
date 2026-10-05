from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from backend.app import models  # noqa: F401
from backend.app.database import Base

dialect = postgresql.dialect()
ddl = []
for table in Base.metadata.sorted_tables:
    ddl.append(str(CreateTable(table).compile(dialect=dialect)) + ";")
    ddl.extend(str(CreateIndex(index).compile(dialect=dialect)) + ";" for index in table.indexes)
Path("database/schema.sql").write_text("\n\n".join(ddl), encoding="utf-8")
