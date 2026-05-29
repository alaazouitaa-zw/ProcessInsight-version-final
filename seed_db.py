from app import app
from models import db
from db_migrate import sync_component_catalog


def init_db():
    with app.app_context():
        db.create_all()
        sync_component_catalog()
        print("Database seeded from component_catalog.")


if __name__ == '__main__':
    init_db()
