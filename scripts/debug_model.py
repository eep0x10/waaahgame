import sys
sys.path.insert(0, "/app")
from app import create_app
app = create_app()
with app.app_context():
    from app.models.game import Unit, Faction
    units = Unit.query.join(Faction).filter(Faction.slug == "beasts-of-chaos").all()
    print(f"Units: {len(units)}")
    for u in units[:5]:
        print(f"  {u.name} -> category={getattr(u, 'unit_category', 'ATTR_MISSING')}")
    # Check if column exists in mapper
    cols = [c.key for c in Unit.__table__.columns]
    print(f"Unit model columns: {cols}")
