"""Phase 2 smoke test — run inside container."""
import re, sys
sys.path.insert(0, '/app')
from app import create_app
from app.extensions import db
from app.models.army import Army

app = create_app()

errors = []

with app.test_client() as client:
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'
            sess['_fresh'] = True

        # ── 1. armies/show renders faction-rules-panel for Seraphon ──
        resp = client.get('/armies/1')
        assert resp.status_code == 200, f"show status {resp.status_code}"
        data = resp.data.decode('utf-8')
        assert 'faction-rules-panel' in data, "faction-rules-panel missing"
        assert 'Regras da Fac' in data, "panel title missing"
        assert 'Tra' in data, "battle traits missing"
        print("OK  armies/show — faction-rules-panel rendered")

        # ── 2. select-formation route ──
        csrf_m = re.search(r'name="csrf_token" value="([^"]+)"', data)
        token = csrf_m.group(1) if csrf_m else ''
        resp2 = client.post('/armies/1/select-formation',
            data={'formation_name': 'CELESTIAL TRANSLOCATION', 'csrf_token': token},
            headers={'HX-Request': 'true', 'X-CSRFToken': token})
        assert resp2.status_code == 200, f"select-formation status {resp2.status_code}"
        data2 = resp2.data.decode('utf-8')
        assert 'faction-rules-panel' in data2, "HTMX partial missing panel"
        assert 'Selecionado' in data2, "selected badge missing"
        print("OK  select-formation — returns HTMX partial with Selecionado badge")

        # ── 3. DB actually saved ──
        army = db.session.get(Army, 1)
        db.session.refresh(army)
        assert army.formation_id == 'CELESTIAL TRANSLOCATION', f"DB not saved: {army.formation_id}"
        print("OK  formation_id persisted to DB:", army.formation_id)

        # ── 4. select-lore (spell) route ──
        resp3 = client.post('/armies/1/select-lore',
            data={'lore_type': 'spell', 'lore_name': 'Celestial Harmony', 'csrf_token': token},
            headers={'HX-Request': 'true', 'X-CSRFToken': token})
        assert resp3.status_code == 200, f"select-lore status {resp3.status_code}"
        db.session.refresh(army)
        assert army.spell_lore_id == 'Celestial Harmony', f"spell_lore_id not saved: {army.spell_lore_id}"
        print("OK  select-lore (spell) persisted:", army.spell_lore_id)

        # ── 5. unit detail has lore section ──
        resp4 = client.get('/units/slann-starmaster')
        assert resp4.status_code == 200
        data4 = resp4.data.decode('utf-8')
        assert 'unit-lore-section' in data4, "unit-lore-section missing"
        assert 'Lore da Unidade' in data4, "lore title missing"
        print("OK  unit detail — lore section rendered")

        # ── 6. summary panel has faction picks ──
        resp5 = client.get('/armies/1')
        data5 = resp5.data.decode('utf-8')
        assert 'Escolhas da Fac' in data5, "summary faction picks missing"
        print("OK  summary panel — faction picks displayed")

        # ── 7. faction without rules shows placeholder ──
        # Army 3 is Aeldari (no rules)
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'
            sess['_fresh'] = True
        army3 = db.session.get(Army, 3)
        if army3:
            resp6 = client.get(f'/armies/{army3.id}')
            data6 = resp6.data.decode('utf-8')
            assert 'ainda n' in data6 or 'placeholder' in data6.lower() or 'não importadas' in data6, \
                "placeholder not shown for faction without rules"
            print("OK  faction without rules — placeholder shown")
        else:
            print("SKIP army 3 not found")

print("\nAll Phase 2 smoke tests PASSED")
