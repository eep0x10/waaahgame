# waaahgame

A wargaming companion app. Currently: Phase 0 scaffold.

## Setup (Windows)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Database

```powershell
flask --app run.py db init
flask --app run.py db migrate -m "init"
flask --app run.py db upgrade
```

## Run

```powershell
python run.py
```

App will be available at http://localhost:5555

## Tests

```powershell
pytest
```

## Roadmap

- **Phase 0** (done) — scaffold: Flask factory, SocketIO, HTMX, SQLAlchemy, migrations, smoke test
- **Phase 1** — auth + friends: Flask-Login, bcrypt, user registration/login, friend list
- **Phase 2** — AoS rules + content: factions, unit cards, core rules reference
- **Phase 3** — army builder: list creation, point tracking, validation
- **Phase 4** — match tracking: game log, results, statistics per army/player
- **Phase 5** — 40k expansion: parallel content layer for Warhammer 40,000
