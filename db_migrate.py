"""Migration SQLite et synchronisation du catalogue de composants."""
from sqlalchemy import inspect, text

from models import db, Component
from component_catalog import COMPONENT_CATALOG

NEW_COLUMNS = {
    "is_solvent": "BOOLEAN DEFAULT 0",
    "hansen_d": "FLOAT",
    "hansen_p": "FLOAT",
    "hansen_h": "FLOAT",
    "mw": "FLOAT",
    "dielectric": "FLOAT",
    "solvent_class": "VARCHAR(30)",
}

SAVED_SIMULATION_COLUMNS = {
    "share_token": "VARCHAR(64)",
    "is_shared": "BOOLEAN DEFAULT 1",
    "inputs_json": "TEXT",
    "results_json": "TEXT",
}


def ensure_component_schema():
    """Ajoute les colonnes manquantes sur SQLite sans recréer la base."""
    insp = inspect(db.engine)
    if "components" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("components")}
    for col, typedef in NEW_COLUMNS.items():
        if col not in existing:
            db.session.execute(text(f"ALTER TABLE components ADD COLUMN {col} {typedef}"))
    db.session.commit()


def ensure_saved_simulation_schema():
    insp = inspect(db.engine)
    if "saved_simulations" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("saved_simulations")}
    for col, typedef in SAVED_SIMULATION_COLUMNS.items():
        if col not in existing:
            db.session.execute(text(f"ALTER TABLE saved_simulations ADD COLUMN {col} {typedef}"))
    db.session.commit()


def _apply_catalog_fields(comp, entry):
    hd, hp, hh = entry.get("hansen", (16.0, 0.0, 0.0))
    comp.name = entry["name"]
    comp.formula = entry["formula"]
    comp.antoine_A = entry["antoine"][0]
    comp.antoine_B = entry["antoine"][1]
    comp.antoine_C = entry["antoine"][2]
    comp.tc = entry["tc"]
    comp.pc = entry["pc"]
    comp.omega = entry["omega"]
    comp.polarity = entry.get("polarity", "non-polar")
    comp.is_solvent = bool(entry.get("is_solvent", False))
    comp.hansen_d = hd
    comp.hansen_p = hp
    comp.hansen_h = hh
    comp.mw = entry.get("mw")
    comp.dielectric = entry.get("dielectric")
    comp.solvent_class = entry.get("solvent_class")


def sync_component_catalog():
    """Insère ou met à jour tous les composants du catalogue."""
    ensure_component_schema()
    ensure_saved_simulation_schema()
    for entry in COMPONENT_CATALOG:
        legacy_name = entry["name"].encode("utf-8").decode("cp1252", errors="ignore")
        comp = Component.query.filter(Component.name.in_([entry["name"], legacy_name])).first()
        if not comp:
            comp = Component(name=entry["name"], formula=entry["formula"],
                             antoine_A=0, antoine_B=0, antoine_C=0)
            db.session.add(comp)
        _apply_catalog_fields(comp, entry)
    db.session.commit()


def get_solvent_components():
    """Liste des solvants marqués ; repli sur catalogue si colonne absente."""
    ensure_component_schema()
    solvents = Component.query.filter_by(is_solvent=True).all()
    if solvents:
        return solvents
    names = {c["name"] for c in COMPONENT_CATALOG if c.get("is_solvent")}
    return Component.query.filter(Component.name.in_(names)).all()
