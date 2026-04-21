# MySQL (legacy)

Previous MySQL connector. Functional but architecturally questionable:
`MySQLConnection.configure()` generates CREATE TABLE statements per CIM class
and stores list/Optional-object fields as JSON in VARCHAR(255) or JSON
columns. Fast at read time but not a sound relational schema, and would
horrify a SQL DBA.

## Files

- `mysql_connection.py` — full connection + schema generator + upload logic
- `mysql_uploader.py` — empty stub that only raised `NotImplementedError`
- `mysql_downloader.py` — same
- `blazegraph_to_mysql.py` — stub batch handler (`pass` body)

## Why it was archived

User wants to rewrite the MySQL integration against Apache AGE (a PostgreSQL
extension that adds property-graph storage). That lets CIM relationships map
onto real graph edges instead of JSON-in-VARCHAR. See `design/TODO.md`.

## If you need it

```python
import sys
sys.path.insert(0, 'archive/mysql_legacy')
from mysql_connection import MySQLConnection
```

Note: `mysql_connection.py` imports from `cimloader.databases` and
`cimgraph.*` — those imports still resolve, so the file runs, but it's
intentionally out of the public package.
