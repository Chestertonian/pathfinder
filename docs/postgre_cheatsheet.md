---

# PostgreSQL Terminal Cheat Sheet (Local)

## Assumptions

| Item                | Value                                                                      |
| ------------------- | -------------------------------------------------------------------------- |
| PostgreSQL binaries | `C:\Users\lukeg\postgres\postgresql-18.4-1-windows-x64-binaries\pgsql\bin` |
| Data directory      | `C:\Users\lukeg\pgdata`                                                    |
| Default database    | `pathfinder`                                                               |
| User                | `lukeg`                                                                    |

---

# Server Control

| Action         | Command                                   |
| -------------- | ----------------------------------------- |
| Start server   | `pg_ctl -D C:\Users\lukeg\pgdata start`   |
| Stop server    | `pg_ctl -D C:\Users\lukeg\pgdata stop`    |
| Restart server | `pg_ctl -D C:\Users\lukeg\pgdata restart` |

---

# Connecting (psql)

| Scenario                           | Command                       |
| ---------------------------------- | ----------------------------- |
| Connect to app DB                  | `psql -U lukeg -d pathfinder` |
| Connect to system DB               | `psql -U lukeg -d postgres`   |
| Default connection (tries user DB) | `psql`                        |

---

# Inside `psql` Commands

| Action              | Command         |
| ------------------- | --------------- |
| List databases      | `\l`            |
| Connect to database | `\c pathfinder` |
| List tables         | `\dt`           |
| Describe table      | `\d users`      |
| Detailed table view | `\d+`           |
| Exit                | `\q`            |

---

# Database Operations

| Action           | SQL                                                      |
| ---------------- | -------------------------------------------------------- |
| Create database  | `CREATE DATABASE pathfinder;`                            |
| Drop database    | `DROP DATABASE pathfinder;`                              |
| Create user      | `CREATE USER myuser WITH PASSWORD 'mypassword';`         |
| Grant privileges | `GRANT ALL PRIVILEGES ON DATABASE pathfinder TO myuser;` |

---

# Running SQL Files

| Task                    | Command                                              |
| ----------------------- | ---------------------------------------------------- |
| Run schema/dump         | `psql -U lukeg -d pathfinder -f schema.sql`          |
| Run file with full path | `psql -U lukeg -d pathfinder -f C:\path\to\file.sql` |

---

# Backup and Restore

| Task             | Command                                     |
| ---------------- | ------------------------------------------- |
| Backup database  | `pg_dump -U lukeg pathfinder > backup.sql`  |
| Restore database | `psql -U lukeg -d pathfinder -f backup.sql` |

---

# Python Connection String

| Case          | Value                                              |
| ------------- | -------------------------------------------------- |
| No password   | `postgresql://lukeg@localhost/pathfinder`          |
| With password | `postgresql://lukeg:password@localhost/pathfinder` |

---

# Python Test

```python
import psycopg

conn = psycopg.connect("postgresql://lukeg@localhost/pathfinder")
cur = conn.cursor()
cur.execute("SELECT 1")
print(cur.fetchone())
```

---

# Common Issues

## Role does not exist

```sql
CREATE ROLE lukeg WITH LOGIN SUPERUSER;
```

---

## Database does not exist

```sql
CREATE DATABASE pathfinder;
```

---

## Server not running

```cmd
pg_ctl -D C:\Users\lukeg\pgdata start
```

---

## Port conflict (use 5433)

Start on alternate port:

```cmd
pg_ctl -D C:\Users\lukeg\pgdata -o "-p 5433" start
```

Connect:

```cmd
psql -U lukeg -p 5433 -d pathfinder
```

---

# Mental Model

| Component    | Meaning                        |
| ------------ | ------------------------------ |
| `pg_ctl`     | Starts/stops PostgreSQL server |
| `psql`       | Command-line client            |
| `pgdata`     | Physical database storage      |
| `pathfinder` | A database inside PostgreSQL   |

---
