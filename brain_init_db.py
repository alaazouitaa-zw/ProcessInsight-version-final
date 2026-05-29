import os
from app import app, db

# Chemin de la DB
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'thermo.db')

if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Ancienne base de données {db_path} supprimée.")

with app.app_context():
    db.create_all()
    print("Nouvelle base de données créée avec le schéma complet.")
    
    # Création d'un Admin par défaut
    from models import User, Component
    from werkzeug.security import generate_password_hash
    
    if not User.query.filter_by(username="ProcessInsight").first():
        admin = User(
            username="ProcessInsight",
            password_hash=generate_password_hash("admin123", method='pbkdf2:sha256'),
            is_admin=True,
            is_verified=True,
            first_name="Admin", last_name="ProcessInsight",
            email="appthermoadmin@gmail.com", city_country="Maroc",
            age=35, profession="Administrateur"
        )
        db.session.add(admin)

    # Ajout des composants chimiques standards
    components_data = [
        {"name": "Benzène", "formula": "C6H6", "A": 6.03056, "B": 1211.033, "C": -52.36, "tc": 562.1, "pc": 4890, "omega": 0.212},
        {"name": "Toluène", "formula": "C7H8", "A": 6.07811, "B": 1343.943, "C": -53.57, "tc": 591.8, "pc": 4100, "omega": 0.264},
        {"name": "Éthanol", "formula": "C2H6O", "A": 8.04494, "B": 1554.3, "C": 222.65, "tc": 513.9, "pc": 6140, "omega": 0.645},
        {"name": "Eau", "formula": "H2O", "A": 8.07131, "B": 1730.63, "C": 233.426, "tc": 647.1, "pc": 22060, "omega": 0.344},
        {"name": "Méthanol", "formula": "CH4O", "A": 8.08097, "B": 1582.27, "C": 239.73, "tc": 512.6, "pc": 8090, "omega": 0.566},
        {"name": "Acétone", "formula": "C3H6O", "A": 7.02447, "B": 1161.0, "C": 224.0, "tc": 508.1, "pc": 4700, "omega": 0.307},
        {"name": "n-Heptane", "formula": "C7H16", "A": 6.9024, "B": 1268.1, "C": 216.9, "tc": 540.2, "pc": 2740, "omega": 0.349},
        {"name": "Cyclohexane", "formula": "C6H12", "A": 6.8413, "B": 1201.5, "C": 222.6, "tc": 553.5, "pc": 4070, "omega": 0.212},
        {"name": "n-Octane", "formula": "C8H18", "A": 6.9096, "B": 1355.1, "C": 209.5, "tc": 568.7, "pc": 2490, "omega": 0.399},
        {"name": "Isopropanol", "formula": "C3H8O", "A": 8.1178, "B": 1580.9, "C": 219.6, "tc": 508.3, "pc": 4760, "omega": 0.667}
    ]

    for comp in components_data:
        if not Component.query.filter_by(name=comp["name"]).first():
            c = Component(
                name=comp["name"], formula=comp["formula"],
                antoine_A=comp["A"], antoine_B=comp["B"], antoine_C=comp["C"],
                tc=comp["tc"], pc=comp["pc"], omega=comp["omega"]
            )
            db.session.add(c)

    db.session.commit()
    print("Nouvelle base de données créée avec 10 composants opérationnels.")

