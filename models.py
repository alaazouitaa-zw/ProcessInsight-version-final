from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import datetime
import secrets

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Nouveaux champs informations personnelles
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    city_country = db.Column(db.String(150), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    profession = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), nullable=True)
    reset_token = db.Column(db.String(100), nullable=True)


class UsageStat(db.Model):
    __tablename__ = 'usage_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) 
    ip_address = db.Column(db.String(50))
    country = db.Column(db.String(100))
    login_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    session_duration_minutes = db.Column(db.Float, default=0.0)

class SavedSimulation(db.Model):
    __tablename__ = 'saved_simulations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    process_type = db.Column(db.String(50), default="distillation")
    comp1_name = db.Column(db.String(100))
    comp2_name = db.Column(db.String(100))
    comp3_name = db.Column(db.String(100), nullable=True)
    temperature = db.Column(db.Float)
    pressure = db.Column(db.Float)
    x1 = db.Column(db.Float)
    
    model_used = db.Column(db.String(50))
    p_bubble = db.Column(db.Float)
    y1 = db.Column(db.Float)
    share_token = db.Column(db.String(64), unique=True, nullable=True, default=lambda: secrets.token_urlsafe(24))
    is_shared = db.Column(db.Boolean, default=True)
    inputs_json = db.Column(db.Text, nullable=True)
    results_json = db.Column(db.Text, nullable=True)

class Component(db.Model):
    __tablename__ = 'components'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    formula = db.Column(db.String(50), nullable=False)
    
    antoine_A = db.Column(db.Float, nullable=False)
    antoine_B = db.Column(db.Float, nullable=False)
    antoine_C = db.Column(db.Float, nullable=False)
    
    tc = db.Column(db.Float, nullable=True)
    pc = db.Column(db.Float, nullable=True) 
    omega = db.Column(db.Float, nullable=True) 
    polarity = db.Column(db.String(20), default="non-polar")
    is_solvent = db.Column(db.Boolean, default=False)
    hansen_d = db.Column(db.Float, nullable=True)
    hansen_p = db.Column(db.Float, nullable=True)
    hansen_h = db.Column(db.Float, nullable=True)
    mw = db.Column(db.Float, nullable=True)
    dielectric = db.Column(db.Float, nullable=True)
    solvent_class = db.Column(db.String(30), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "formula": self.formula,
            "antoine": {"A": self.antoine_A, "B": self.antoine_B, "C": self.antoine_C},
            "tc": self.tc, "pc": self.pc, "omega": self.omega, "polarity": self.polarity,
            "is_solvent": self.is_solvent,
            "hansen": {"d": self.hansen_d, "p": self.hansen_p, "h": self.hansen_h},
            "mw": self.mw, "dielectric": self.dielectric, "solvent_class": self.solvent_class,
        }
