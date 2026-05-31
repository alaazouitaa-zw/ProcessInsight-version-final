from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, session, abort
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import datetime
import json
import requests
import secrets
from functools import wraps
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from distillation_engine import run_full_distillation
from models import db, Component, User, UsageStat, SavedSimulation
from db_migrate import sync_component_catalog, get_solvent_components
import thermo_engine
import absorption_engine
import optimization_engine
import diagnostic_engine
import distillation_engine

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_fallback_secret_key')
app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', '')
CORS(app)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'thermo.db')
basedir = os.path.abspath(os.path.dirname(__file__))

db_url = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'thermo.db'))
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

ADMIN_USERNAME = "ProcessInsight"
ADMIN_PASSWORD = "admin123"

def is_platform_admin(user):
    return (
        user.is_authenticated
        and user.username == ADMIN_USERNAME
        and bool(user.is_admin)
    )

def ensure_platform_admin():
    admin = User.query.filter_by(username=ADMIN_USERNAME).first()
    if not admin:
        admin = User(
            username=ADMIN_USERNAME,
            first_name="Admin",
            last_name="ProcessInsight",
            email="appthermoadmin@gmail.com",
            city_country="Maroc",
            age=35,
            profession="Administrateur",
            is_verified=True
        )
        db.session.add(admin)

    admin.password_hash = generate_password_hash(ADMIN_PASSWORD, method='pbkdf2:sha256')
    admin.is_admin = True
    admin.is_verified = True
    admin.verification_token = None

    User.query.filter(User.username != ADMIN_USERNAME).update(
        {User.is_admin: False},
        synchronize_session=False
    )
    db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_platform_admin(current_user):
            flash("Accès refusé.")
            return redirect(url_for('config_page'))
        return f(*args, **kwargs)
    return decorated_function

# --- INTERNATIONALISATION ---
translations = {
    "fr": {
        "title": "Nouvelle Simulation", "history": "Mon Historique", "admin_panel": "Panel Admin", "logout": "Quitter",
        "lang": "fr", "config": "Configuration du Procédé", "sim": "Simuler le Procédé",
        "results": "Résultats Intégraux", "profile": "Mon Profil"
    }
}

@app.context_processor
def inject_translations():
    lang = 'fr'
    session['lang'] = lang
    return dict(
        lang=lang,
        _t=lambda key: translations[lang].get(key, key),
        is_platform_admin=is_platform_admin
    )

with app.app_context():
    db.create_all()
    sync_component_catalog()
    ensure_platform_admin()

# --- ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if not user:
            flash("Ce compte n'existe pas. Veuillez vous inscrire.", "auth_error")
            return redirect(url_for('index'))
            
        if not check_password_hash(user.password_hash, password):
            flash("Mot de passe incorrect.", "auth_error")
            return redirect(url_for('index'))
            
        if not user.is_verified:
            flash("Veuillez vérifier votre adresse email avant de vous connecter.", "auth_error")
            return redirect(url_for('index'))
            
        login_user(user)
        
        # Tracking IP & Pays
        ip = request.remote_addr
        country = "Local/Unknown"
        try:
            # Appel API externe pour géolocalisation (ip-api.com est gratuit et sans clé)
            geo_resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=2).json()
            if geo_resp.get('status') == 'success':
                country = geo_resp.get('country', 'Unknown')
        except: pass
        
        db.session.add(UsageStat(user_id=user.id, ip_address=ip, country=country))
        db.session.commit()
        
        return redirect(url_for('select_page'))
        
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        if User.query.filter_by(username=username).first():
            flash("Ce nom d'utilisateur existe déjà.", "auth_error")
            return redirect(url_for('index'))
            
        import re
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_pattern, email):
            flash("Format d'adresse email invalide.", "auth_error")
            return redirect(url_for('index'))
            
        if User.query.filter_by(email=email).first():
            flash("Cette adresse email est déjà utilisée.", "auth_error")
            return redirect(url_for('index'))
            
        hashed_pw = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256')
        import secrets
        v_token = secrets.token_hex(16)
        
        new_user = User(
            username=username, 
            password_hash=hashed_pw, 
            is_admin=False,
            is_verified=False,
            verification_token=v_token,
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            email=email,
            city_country=request.form.get('city_country'),
            age=request.form.get('age', type=int),
            profession=request.form.get('profession')
        )
        db.session.add(new_user)
        db.session.commit()
        
        from mail_helper import send_verification_email
        try:
            send_verification_email(email, v_token)
        except Exception as e:
            print(f"SMTP Email Send Failed: {e}")
            
        print(f"LOCAL VERIFICATION LINK FOR {username}: http://127.0.0.1:5000/verify/{v_token}")
        
        flash("Inscription réussie ! Veuillez vérifier votre boîte mail pour activer votre compte.", "auth_success")
        return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html', user=current_user)

@app.route('/contact', methods=['POST'])
def contact():
    name = (request.form.get('name') or '').strip()
    email = (request.form.get('email') or '').strip()
    subject = (request.form.get('subject') or '').strip()
    message = (request.form.get('message') or '').strip()

    if not all([name, email, subject, message]):
        flash("Veuillez remplir tous les champs du formulaire de contact.", "contact_error")
        return redirect(url_for('index') + '#contact-section')

    import re
    email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(email_pattern, email):
        flash("Veuillez saisir une adresse e-mail valide.", "contact_error")
        return redirect(url_for('index') + '#contact-section')

    from mail_helper import send_contact_email
    if send_contact_email(name, email, subject, message):
        flash("Message envoyé avec succès ! Notre équipe vous contactera sous 24h.", "contact_success")
    else:
        flash("Erreur lors de l'envoi du message. Veuillez réessayer.", "contact_error")

    return redirect(url_for('index') + '#contact-section')

@app.route('/select')
@login_required
def select_page():
    return render_template('select.html', user=current_user)

@app.route('/config', methods=['GET', 'POST'])
@login_required
def config_page():
    selected = request.args.getlist('process')
    if not selected and request.method == 'POST':
        selected = request.form.getlist('process')
        
    if not selected:
        return redirect(url_for('select_page'))
    allowed_processes = {
        'distillation',
        'flash',
        'absorption',
        'extraction',
        'pump',
        'compressor',
        'heat_exchanger',
    }
    selected = [process for process in selected if process in allowed_processes]
    selected = list(dict.fromkeys(selected))
    if not selected:
        flash("Veuillez sélectionner au moins un procédé valide.")
        return redirect(url_for('select_page'))
        
    return render_template('config.html', 
                           components=Component.query.order_by(Component.name).all(),
                           solvents=get_solvent_components(),
                           user=current_user, 
                           selected_processes=selected)

@app.route('/load_sim/<int:sim_id>')
@login_required
def load_sim(sim_id):
    from models import SavedSimulation
    sim = SavedSimulation.query.get_or_404(sim_id)
    if sim.user_id != current_user.id:
        flash("Accès refusé.")
        return redirect(url_for('history_page'))
    selected = sim.process_type.split(',') if sim.process_type else ['distillation']
    return render_template(
        'config.html',
        components=Component.query.order_by(Component.name).all(),
        solvents=get_solvent_components(),
        user=current_user,
        sim=sim,
        selected_processes=selected,
    )

@app.route('/simulate', methods=['GET', 'POST'])
@login_required
def simulate_page():
    if request.method == 'GET': return redirect(url_for('config_page'))
    
    process_types = request.form.getlist('process_types')
    if not process_types:
        p_single = request.form.get('process_type')
        if p_single:
            process_types = [p_single]
        else:
            return redirect(url_for('config_page'))
    absorption_only = len(process_types) == 1 and process_types[0] == 'absorption'

    comp1 = None
    comp2 = None
    comp3 = None
    if not absorption_only:
        comp1 = Component.query.get(request.form.get('comp1_id', type=int))
        comp2 = Component.query.get(request.form.get('comp2_id', type=int))
        comp3_id = request.form.get('comp3_id')
        comp3 = Component.query.get(int(comp3_id)) if comp3_id else None

    T = request.form.get('temperature', 80.0, type=float)
    P_sys = request.form.get('pressure', 101.325, type=float)
    x1 = request.form.get('x1', 0.5, type=float)
    x2 = request.form.get('x2', None, type=float)
    mode_compare = request.form.get('mode_compare')

    absorption_only = len(process_types) == 1 and process_types[0] == 'absorption'
    if absorption_only:
        model_used = 'absorption_packed'
        model_explanation = 'Mode absorption seule, utilisation des paramètres dédiés gaz/liquide.'
        data = {
            "K1": request.form.get('abs_m', 1.5, type=float),
            "K2": 1.0,
            "P_bubble": P_sys,
            "P_dew": P_sys,
            "T_bubble": T,
            "T_dew": T + 5,
            "y1": x1,
            "y2": 1 - x1,
            "y3": 0,
            "Z_factor": 1.0,
            "gamma1": 1.0,
            "gamma2": 1.0,
            "alpha": request.form.get('abs_m', 1.5, type=float),
            "diagrams": {
                "xy": [],
                "pxy": [],
                "txy": [],
                "profile": [],
                "effect_t": [],
                "effect_p": []
            }
        }
        insights = {}
    else:
        model_data = thermo_engine.auto_select_model(T, P_sys, comp1, comp2, comp3, mode=mode_compare)
        model_used = model_data["model"]
        model_explanation = model_data["explanation"]
        # Nouveau moteur scientifique intégral
        data = thermo_engine.calculate_science_matrices(model_used, x1, T, P_sys, comp1, comp2, comp3, x2=x2)
        insights = optimization_engine.get_insights(data["y1"], x1, T, P_sys, comp1, data["P_bubble"])
    
    op_results = {}
    for p_type in process_types:
        if p_type == 'distillation':
            x_d = request.form.get('dist_x_d', request.form.get('x_d', 0.95, type=float), type=float)
            x_b = request.form.get('dist_x_b', request.form.get('x_b', 0.05, type=float), type=float)
            reflux = request.form.get('dist_reflux', request.form.get('reflux', 1.5, type=float), type=float)
            feed_q = request.form.get('dist_feed_q', request.form.get('feed_q', 1.0, type=float), type=float)
            dist_flow_f = request.form.get('dist_flow_f', 100.0, type=float)
            
            # Utiliser le nouveau moteur de distillation avancé
            mccabe = distillation_engine.calculate_distillation_advanced(
                F_flow=dist_flow_f, x_f=x1, x_d=x_d, x_b=x_b, R=reflux, q=feed_q,
                P_kpa=P_sys, comp1=comp1, comp2=comp2, model_type=model_used,
                tray_eff=0.75
            )
            
            # Ajouter les infos de qualité q
            if mccabe.get("success"):
                mccabe["q_info"] = distillation_engine.calculate_q_properties(
                    feed_q, x1, comp1, comp2, P_sys, model_used
                )
            
            op_results["distillation"] = mccabe
            op_results["mccabe"] = mccabe  # diagnostics compatibility

        elif p_type == 'pump':
            flow = request.form.get('pump_flow_rate', request.form.get('flow_rate', 10.0, type=float), type=float)
            p_out = request.form.get('pump_p_out', request.form.get('p_out', P_sys + 100, type=float), type=float)
            eff = request.form.get('pump_efficiency', request.form.get('efficiency', 0.75, type=float), type=float)
            op_results["pump"] = thermo_engine.calculate_pump(flow, P_sys, p_out, eff)
        elif p_type == 'compressor':
            flow = request.form.get('comp_flow_rate', request.form.get('flow_rate', 100.0, type=float), type=float)
            p_out = request.form.get('comp_p_out', request.form.get('p_out', P_sys + 500, type=float), type=float)
            eff = request.form.get('comp_efficiency', request.form.get('efficiency', 0.75, type=float), type=float)
            op_results["compressor"] = thermo_engine.calculate_compressor(flow, T, P_sys, p_out, eff)
        elif p_type == 'heat_exchanger':
            flow = request.form.get('hex_flow_rate', request.form.get('flow_rate', 1000.0, type=float), type=float)
            t_out = request.form.get('hex_t_out', request.form.get('t_out', T + 40, type=float), type=float)
            cp = request.form.get('hex_cp', request.form.get('cp', 2.0, type=float), type=float)
            op_results["heat_exchanger"] = thermo_engine.calculate_heat_exchanger(flow, cp, T, t_out)
        elif p_type == 'extraction':
            L = request.form.get('ext_flow_l', 100.0, type=float)
            V = request.form.get('ext_flow_v', 150.0, type=float)
            xn = request.form.get('ext_xn', 0.02, type=float)
            ys = request.form.get('ext_ys', 0.0, type=float)
            K = data.get("K1", 1.5)
            if K < 0.1: K = 1.5
            op_results["extraction"] = thermo_engine.calculate_lle_stages(x1, xn, ys, V, L, K)
        elif p_type == 'absorption':
            y_in = request.form.get('abs_y_in', 0.05, type=float)
            y_out = request.form.get('abs_y_out', 0.005, type=float)
            x_in = request.form.get('abs_x_in', 0.0, type=float)
            G = request.form.get('abs_flow_g', 1000.0, type=float)
            L = request.form.get('abs_flow_l', 1500.0, type=float)
            abs_type = request.form.get('abs_type', 'physical')
            flow_direction = request.form.get('abs_flow_direction', 'counter_current')
            T_gas = request.form.get('abs_T_gas', 40.0, type=float)
            T_liq = request.form.get('abs_T_liq', 25.0, type=float)
            abs_m = request.form.get('abs_m', 1.5, type=float)
            rho_l = request.form.get('abs_rho_l', 1000.0, type=float)
            mu_l = request.form.get('abs_mu_l', 0.001, type=float)
            MW_l = request.form.get('abs_MW_l', 18.0, type=float)
            column_d = request.form.get('abs_column_d', 0.6, type=float)
            hetp = request.form.get('abs_hetp', 0.5, type=float)
            tray_eff = request.form.get('abs_tray_eff', 0.65, type=float)
            op_results["absorption"] = absorption_engine.calculate_gas_absorption(
                y_in,
                y_out,
                x_in,
                G,
                L,
                abs_m,
                column_type="packed",
                absorption_type=abs_type,
                flow_direction=flow_direction,
                T_gas_C=T_gas,
                T_liq_C=T_liq,
                hetp=hetp,
                tray_efficiency=tray_eff,
                rho_l=rho_l,
                mu_l=mu_l,
                MW_l=MW_l,
                column_d=column_d,
            )
        elif p_type == 'flash':
            psi = request.form.get('flash_psi', 0.5, type=float)
            dp = request.form.get('flash_dp', 0.0, type=float)
            t_flash = T - dp * 0.1  # Approximation: température baisse avec la détente
            p_flash = P_sys - dp
            op_results["flash"] = {
                "psi": round(psi, 3),
                "dp": round(dp, 2),
                "t_flash": round(t_flash, 1),
                "p_flash": round(p_flash, 2),
                "flow_v": round(psi * 100, 1),
                "flow_l": round((1 - psi) * 100, 1),
                "success": True,
                "inputs": {
                    "psi": round(psi, 3),
                    "T_in_c": round(T, 1),
                    "P_in_kpa": round(P_sys, 2),
                    "delta_P_kpa": round(dp, 2),
                },
                "outputs": {
                    "T_out_c": round(t_flash, 1),
                    "P_out_kpa": round(p_flash, 2),
                    "V_pct": round(psi * 100, 1),
                    "L_pct": round((1 - psi) * 100, 1),
                    "success": True,
                }
            }

    data["equilibrium"] = {"P_sys": P_sys}
    
    # --- DIAGNOSTIC IA ---
    # On structure les inputs et résultats pour le moteur
    diag_inputs = dict(request.form)
    # Composants par défaut pour absorption seule
    result_components = []
    if comp1 and comp2:
        result_components = [comp1.name, comp2.name] + ([comp3.name] if comp3 else [])
    elif absorption_only:
        result_components = ["Gaz absorbé", "Liquide absorbant"]

    # L'objet results principal
    results = {
        "process_types": process_types,
        "mode_compare": mode_compare,
        "is_ternary": bool(comp3),
        "components": result_components,
        "model_used": model_used,
        "model_explanation": model_explanation,
        "data": data,
        "op_results": op_results,
        "insights": insights,
        "equilibrium": {"T": T, "P_sys": P_sys}
    }
    
    # On appelle le moteur
    all_diagnostics = []
    for p_type in process_types:
        try:
            diag = diagnostic_engine.run_diagnostics(p_type, diag_inputs, results)
            if diag:
                all_diagnostics.extend(diag)
        except Exception as e:
            print(f"Erreur diag {p_type}: {e}")
            
    results["diagnostics"] = all_diagnostics

    # --- SAUVEGARDE AUTOMATIQUE ---
    try:
        from models import SavedSimulation
        share_token = secrets.token_urlsafe(24)
        results["share_token"] = share_token
        new_sim = SavedSimulation(
            user_id=current_user.id,
            process_type=",".join(process_types),
            comp1_name=comp1.name if comp1 else None,
            comp2_name=comp2.name if comp2 else None,
            comp3_name=comp3.name if comp3 else None,
            temperature=T,
            pressure=P_sys,
            x1=x1,
            model_used=model_used,
            p_bubble=data.get("P_bubble"),
            y1=data.get("y1"),
            share_token=share_token,
            is_shared=True,
            inputs_json=json.dumps(dict(request.form), ensure_ascii=False, default=str),
            results_json=json.dumps(results, ensure_ascii=False, default=str)
        )
        db.session.add(new_sim)
        db.session.commit()
        results["saved_simulation_id"] = new_sim.id
        results["share_url"] = url_for('shared_simulation', token=share_token, _external=True)
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la sauvegarde automatique : {e}")

    return render_template('simulation.html', results=results, user=current_user)

@app.route('/distillation', methods=['GET', 'POST'])
@login_required
def distillation_advanced_page():
    components = Component.query.all()
    results = None
    inputs = {
        "comp1_id": 6,  # Éthanol (default volatil)
        "comp2_id": 5,  # Eau (default lourd)
        "F_flow": 100.0,
        "x_f": 0.40,
        "x_d": 0.85,
        "x_b": 0.05,
        "reflux_R": 2.0,
        "q_val": 1.0,
        "q_mode": "state",
        "q_state": "liquid_sat",
        "q_liq_frac": 0.5,
        "q_direct": 1.0,
        "pressure": 101.325,
        "thermo_model": "NRTL",
        "tray_efficiency": 0.75,
        "condenser_type": "total",
        "reboiler_type": "partial"
    }
    
    if request.method == 'POST':
        # Extraction des inputs du formulaire
        comp1_id = request.form.get('comp1_id', 6, type=int)
        comp2_id = request.form.get('comp2_id', 5, type=int)
        F_flow = request.form.get('F_flow', 100.0, type=float)
        x_f = request.form.get('x_f', 0.40, type=float)
        x_d = request.form.get('x_d', 0.85, type=float)
        x_b = request.form.get('x_b', 0.05, type=float)
        reflux_R = request.form.get('reflux_R', 2.0, type=float)
        
        # Qualité d'alimentation (q-factor)
        q_mode = request.form.get('q_mode', 'state')
        q_state = request.form.get('q_state', 'liquid_sat')
        q_liq_frac = request.form.get('q_liq_frac', 0.5, type=float)
        q_direct = request.form.get('q_direct', 1.0, type=float)
        
        if q_mode == 'direct':
            q_val = q_direct
        else:
            state_map = {
                "liquid_sub": 1.3,
                "liquid_sat": 1.0,
                "liq_vap": q_liq_frac,
                "vap_sat": 0.0,
                "vap_super": -0.4
            }
            q_val = state_map.get(q_state, 1.0)
            
        pressure = request.form.get('pressure', 101.325, type=float)
        thermo_model = request.form.get('thermo_model', 'NRTL')
        tray_efficiency = request.form.get('tray_efficiency', 0.75, type=float)
        condenser_type = request.form.get('condenser_type', 'total')
        reboiler_type = request.form.get('reboiler_type', 'partial')
        
        # Conserver les valeurs de formulaire pour l'affichage (sticky)
        inputs.update({
            "comp1_id": comp1_id,
            "comp2_id": comp2_id,
            "F_flow": F_flow,
            "x_f": x_f,
            "x_d": x_d,
            "x_b": x_b,
            "reflux_R": reflux_R,
            "q_val": q_val,
            "q_mode": q_mode,
            "q_state": q_state,
            "q_liq_frac": q_liq_frac,
            "q_direct": q_direct,
            "pressure": pressure,
            "thermo_model": thermo_model,
            "tray_efficiency": tray_efficiency,
            "condenser_type": condenser_type,
            "reboiler_type": reboiler_type
        })
        
        comp1 = Component.query.get(comp1_id)
        comp2 = Component.query.get(comp2_id)
        
        if comp1 and comp2:
            results = distillation_engine.calculate_distillation_advanced(
                F_flow=F_flow, x_f=x_f, x_d=x_d, x_b=x_b, R=reflux_R, q=q_val,
                P_kpa=pressure, comp1=comp1, comp2=comp2, model_type=thermo_model,
                tray_eff=tray_efficiency
            )
            
            if results.get("success"):
                results["comp1"] = comp1
                results["comp2"] = comp2
                results["q_info"] = distillation_engine.calculate_q_properties(
                    q_val, x_f, comp1, comp2, pressure, thermo_model
                )
                
                # Sauvegarde automatique en base
                try:
                    new_sim = SavedSimulation(
                        user_id=current_user.id,
                        process_type="distillation_pro",
                        comp1_name=comp1.name,
                        comp2_name=comp2.name,
                        temperature=results["q_info"]["temperature"],
                        pressure=pressure,
                        x1=x_f,
                        model_used=thermo_model,
                        p_bubble=pressure,
                        y1=x_d
                    )
                    db.session.add(new_sim)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(f"Erreur d'auto-sauvegarde distillation_pro: {e}")
            else:
                flash(results.get("error", "Erreur lors de la simulation."))
                results = None
                
    return render_template(
        'distillation_advanced.html',
        components=components,
        inputs=inputs,
        results=results,
        user=current_user
    )


@app.route('/save_simulation', methods=['POST'])
@login_required
def save_simulation():
    share_token = secrets.token_urlsafe(24)
    sim = SavedSimulation(
        user_id=current_user.id,
        process_type=request.form.get('process_type'),
        comp1_name=request.form.get('comp1_name'),
        comp2_name=request.form.get('comp2_name'),
        model_used=request.form.get('model_used'),
        share_token=share_token,
        is_shared=True,
        inputs_json=json.dumps(dict(request.form), ensure_ascii=False, default=str)
    )
    db.session.add(sim)
    db.session.commit()
    flash("Simulation enregistrée !")
    return redirect(url_for('history_page'))

@app.route('/history')
@login_required
def history_page():
    sims = SavedSimulation.query.filter_by(user_id=current_user.id).order_by(SavedSimulation.saved_at.desc()).limit(20).all()
    return render_template('history.html', sims=sims)

@app.route('/shared/simulation/<token>')
def shared_simulation(token):
    sim = SavedSimulation.query.filter_by(share_token=token, is_shared=True).first_or_404()
    if not sim.results_json:
        flash("Cette simulation ancienne ne contient pas encore les resultats partageables. Relancez la simulation puis partagez le nouveau lien.")
        return redirect(url_for('index'))

    try:
        results = json.loads(sim.results_json)
    except (TypeError, json.JSONDecodeError):
        abort(404)

    results["share_token"] = sim.share_token
    results["share_url"] = url_for('shared_simulation', token=sim.share_token, _external=True)
    results["saved_simulation_id"] = sim.id
    return render_template('simulation.html', results=results, user=None, shared_view=True)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile_page():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.email = request.form.get('email')
        current_user.city_country = request.form.get('city_country')
        current_user.age = request.form.get('age', type=int)
        current_user.profession = request.form.get('profession')
        
        new_password = request.form.get('password')
        if new_password:
            current_user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
            
        db.session.commit()
        flash("Profil mis à jour avec succès !")
        return redirect(url_for('profile_page'))
        
    return render_template('profile.html', user=current_user)

@app.route('/verify/<token>')
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if user:
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        flash("Votre compte a été vérifié avec succès ! Vous pouvez maintenant vous connecter.")
    else:
        flash("Lien de vérification invalide ou expiré.")
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            import secrets
            from mail_helper import send_reset_email
            token = secrets.token_hex(16)
            user.reset_token = token
            db.session.commit()
            
            if send_reset_email(email, token):
                flash("Un email de réinitialisation de mot de passe a été envoyé.")
            else:
                flash("Erreur lors de l'envoi de l'email. Veuillez réessayer.")
        else:
            flash("Cette adresse email n'est pas enregistrée.")
        return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        flash("Lien de réinitialisation invalide ou expiré.")
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas.")
            return render_template('reset_password.html', token=token)
            
        user.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        user.reset_token = None
        db.session.commit()
        flash("Votre mot de passe a été réinitialisé. Vous pouvez maintenant vous connecter.")
        return redirect(url_for('index'))
        
    return render_template('reset_password.html', token=token)


# --- COMPONENT APIs ---
@app.route('/api/components')
@login_required
def api_components():
    components = Component.query.order_by(Component.name).all()
    return jsonify([component.to_dict() for component in components])


# --- SOLVENT SUGGESTION API ---
@app.route('/api/suggest_solvent', methods=['POST'])
@login_required
def suggest_solvent():
    data = request.json
    comp1_id = data.get('comp1_id')
    comp2_id = data.get('comp2_id')
    
    if not comp1_id or not comp2_id:
        return jsonify({"error": "Composants manquants"}), 400

    try:
        comp1_id = int(comp1_id)
        comp2_id = int(comp2_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Identifiants de composants invalides"}), 400
        
    comp1 = Component.query.get(comp1_id)
    comp2 = Component.query.get(comp2_id)
    
    if not comp1 or not comp2:
        return jsonify({"error": "Composants non trouvés"}), 404
        
    potential_solvents = [
        solvent for solvent in get_solvent_components()
        if solvent.id not in {comp1_id, comp2_id}
    ]
    
    suggestions = []
    for s in potential_solvents:
        score = 0
        reason = []
        
        # Affinité avec le soluté
        if s.polarity == comp1.polarity:
            score += 2
            reason.append(f"Forte affinité avec le soluté ({comp1.name}) car tous deux sont {s.polarity}s.")
        else:
            reason.append(f"Faible affinité avec le soluté (polarités différentes).")
            
        # Répulsion avec le diluant
        if s.polarity != comp2.polarity:
            score += 1
            reason.append(f"Faible miscibilité avec le diluant ({comp2.name}), ce qui est idéal pour créer deux phases distinctes.")
        else:
            reason.append(f"Risque de miscibilité avec le diluant (mêmes polarités).")
            
        if score >= 2:
            suggestions.append({
                "id": s.id, 
                "name": s.name, 
                "score": score,
                "reason": " ".join(reason)
            })
            
    # Trier par score décroissant
    suggestions.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({"suggestions": suggestions[:3]})

# --- ROUTE IA COPILOT ---
from agent_ai import ProcessInsightCopilot

@app.route('/api/ask_ai', methods=['POST'])
@login_required
def ask_ai():
    data = request.get_json(silent=True) or {}
    api_key = data.get('api_key') or app.config.get('GEMINI_API_KEY')
    context_data = data.get('context_data', {})
    user_question = data.get('question', None)
    
    # Save the key in session for future requests if provided in request
    if data.get('api_key'):
        session['gemini_api_key'] = api_key
    elif not api_key:
        api_key = session.get('gemini_api_key')
        
    try:
        copilot = ProcessInsightCopilot()
        answer = copilot.generate_expert_analysis(api_key, context_data, user_question)
    except Exception as exc:
        app.logger.exception("AI copilot error")
        answer = (
            "Je peux repondre a votre question, mais le moteur IA a rencontre "
            f"une erreur interne temporaire: {exc}"
        )

    return jsonify({"answer": answer})

@app.route('/admin')
@admin_required
def admin_dashboard():
    all_users = User.query.all()
    all_stats = UsageStat.query.order_by(UsageStat.login_time.desc()).all()
    all_sims = SavedSimulation.query.order_by(SavedSimulation.saved_at.desc()).all()
    
    # Calcul des statistiques simplifiées
    stats_summary = {
        "total_users": len(all_users),
        "total_sims": len(all_sims),
        "total_logins": len(all_stats),
        "student_count": len([u for u in all_users if u.profession == "Étudiant"]),
        "engineer_count": len([u for u in all_users if u.profession == "Ingénieur"])
    }
    
    return render_template('admin_dashboard.html', 
        users=all_users, 
        stats=all_stats, 
        sims=all_sims,
        summary=stats_summary
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
