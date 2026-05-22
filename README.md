# WaaahGame

Companion app multi-wargame em Português (PT-BR), com foco inicial em **Warhammer Age of Sigmar 4th Edition** (GHB 2025-26 + Battlescroll Abril 2026), e suporte planejado para Warhammer 40K e Trench Crusade.

## O que faz

- **Compêndio de regras** — Core Rules, Setup, Movimento, Combate, Disparo, Magia, Battle Tactics, Battleplans, Composição de Exército, Regras de Torneio, Glossário — 14 páginas em PT-BR com diagramas SVG didáticos.
- **Catálogo de unidades** — 850+ unidades AoS com stats, pontos, base sizes, keywords. Filtros por facção, role, Legacy.
- **Facções completas** — 26 facções AoS com Battle Traits, Heroic Traits, Artefatos, Spell Lores, Battle Formations.
- **Regimentos de Renome** — 64 Regiments of Renown organizados por Grand Alliance.
- **Builder de exércitos** — montar listas com validação por battlepack (Vanguard 1000pts, Battlehost 2000pts), Cumulative Surcharge, Regiment+Companion checks.
- **Stats & histórico de partidas** — registrar vitórias/derrotas, ver winrate por facção/battleplan.
- **Auth + social** — registro, login, lista de amigos, compartilhamento de listas via link público.

## Stack

- **Backend:** Python 3.11+ · Flask · SQLAlchemy · Alembic · SQLite
- **Frontend:** Jinja2 · HTMX · CSS puro (sem framework JS pesado)
- **Container:** Docker · docker-compose
- **PDFs → Markdown:** pdfplumber (scripts em `scripts/`)

## Quick start

```bash
git clone https://github.com/eep0x10/waaahgame.git
cd waaahgame
docker compose up -d --build
# acessar http://localhost:5555
```

Sem Docker:

```bash
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
pip install -r requirements.txt
cp .env.example .env
flask db upgrade
flask run --port 5555
```

## Estrutura

```
app/
  ├── models/          # SQLAlchemy: Faction, Unit, Army, ArmyUnit, Match, RegimentOfRenown...
  ├── routes/          # Blueprints: rules, factions, units, armies, matches, stats, auth
  ├── services/        # Lógica de validação, formatos, view helpers
  ├── templates/       # Jinja2: layout BB-inspired dark theme
  │   └── rules/aos/   # 14 páginas de regras AoS com diagramas SVG inline
  └── static/
      ├── css/app.css
      └── img/units/   # imagens por facção
scripts/
  └── import_*.py      # scripts de seed/import
migrations/            # Alembic migrations
```

## Status

- AoS 4ed: regras completas (14 páginas), unidades alinhadas com Battle Profiles Abril 2026
- Warhammer 40K: estrutura pronta, conteúdo em progresso
- Trench Crusade: planejado

## Idioma

PT-BR primary. Termos canônicos em inglês são preservados (Battle Tactic, Ward, Rend, Engagement Range, Wholly Within, etc.) — facilita cross-referência com regras oficiais e comunidade.

## Sobre direitos autorais

Este projeto é uma **ferramenta companion não-oficial**. Warhammer Age of Sigmar, Warhammer 40,000, todas as facções, unidades, nomes e iconografia associados são propriedade da Games Workshop Ltd. WaaahGame não é endossado ou afiliado à Games Workshop. Conteúdo de regras é parafraseado em PT-BR para fins didáticos — para regras oficiais completas, consulte os Core Rules, Battletomes e o Generals Handbook publicados pela GW.

## Licença

Código sob MIT. Conteúdo de regras parafraseado — uso pessoal/educacional.

---

Feito com cerveja pra mesa de domingo.
