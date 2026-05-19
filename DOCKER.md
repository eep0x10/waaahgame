## Running with Docker

```sh
# Build
docker compose build

# Start (detached)
docker compose up -d

# Open
open http://localhost:5555

# Logs
docker compose logs -f app

# Stop
docker compose down

# Reset DB (drops volume — all data lost)
docker compose down -v && docker compose up -d
```

### Environment variables

Copy `.env.example` to `.env` and set `SECRET_KEY`:

```sh
cp .env.example .env
# edit .env and set SECRET_KEY
```

If no `.env` file is present, `SECRET_KEY` defaults to `dev-change-me` (not safe for production).

### DB persistence

SQLite data lives in the named volume `waaahgame_data` mounted at `/app/instance`.
Seeds run automatically on every container start (idempotent upserts — safe to re-run).
