# Guide d'Installation & Démarrage Rapide

## ProcessInsight - Module Distillation Avancée v2.0.0

### ⚡ Démarrage Rapide (2 minutes)

#### Option 1: Script Automatique (Windows)
```bash
run.bat
```
Le script va :
1. ✓ Vérifier Python
2. ✓ Installer dépendances
3. ✓ Exécuter tests
4. ✓ Lancer l'application

#### Option 2: Manuel (Tous OS)

**1. Vérifier Python**
```bash
python --version
# Doit afficher Python 3.8 ou supérieur
```

**2. Installer dépendances**
```bash
pip install -r requirements.txt
```

**3. (Optionnel) Tester**
```bash
python integration_test.py
```

**4. Lancer l'application**
```bash
python app.py
```

**5. Ouvrir le navigateur**
```
http://localhost:5000
```

---

## 📋 Prérequis

### Système
- Windows 7+ / macOS 10.12+ / Linux
- 100 MB espace disque
- 4 GB RAM minimum

### Logiciels
- **Python 3.8 ou supérieur** (https://www.python.org/downloads/)
- **pip** (inclus avec Python)

### Dépendances Python
Installées automatiquement par `pip install -r requirements.txt` :
- Flask 3.0+ (framework web)
- NumPy 1.24+ (calculs)
- SciPy 1.10+ (optimisation)
- Plotly 5.14+ (graphiques)
- SQLAlchemy 3.1+ (base de données)

---

## 🚀 Après Démarrage

L'application accède normalement sur **http://localhost:5000**

### Fonctionnalités Disponibles

1. **Dashboard Distillation** (`/distillation_advanced`)
   - Formulaire entrée complète
   - Résultats KPI en temps réel
   - Graphiques interactifs McCabe-Thiele

2. **Module Q-Factor** (`/distillation_q_factor`)
   - 6 états thermiques d'alimentation
   - Saisie directe q
   - Diagrammes x-y et T-x-y

3. **API REST** (`/api/distillation/*`)
   - `POST /api/distillation/full_simulation`
   - `POST /api/distillation/validate`
   - `POST /api/distillation/q_factor_calc`
   - `POST /api/distillation/mccabe_thiele`
   - `POST /api/distillation/energy_analysis`

### Test Simple

Accédez à : http://localhost:5000/distillation_advanced

1. Sélectionner **Eau** (Composé 1) et **Éthanol** (Composé 2)
2. Laisser les valeurs par défaut
3. Cliquer **"Simuler la Distillation"**

**Résultat attendu:**
- N_min ≈ 4.2 étages
- R_min ≈ 0.85
- N_theo ≈ 12.5 étages
- Graphique McCabe-Thiele affiché

---

## 🧪 Validation Complète

Pour vérifier que tout fonctionne :

```bash
# Test 1: Vérifier imports
python test_modules.py

# Test 2: Pipeline complet
python integration_test.py
```

Les deux doivent afficher : **✓ TOUS LES TESTS PASSÉS**

---

## 📁 Structure Répertoire

```
processgroupe.worktrees/agents-distillation-module-development/
├── app.py                              # Application Flask
├── distillation_engine.py              # Cœur distillation
├── validation_engine.py                # (NEW) Validation physique
├── energy_engine.py                    # (NEW) Analyse énergie
├── pedagogical_mode.py                 # (NEW) Mode pédagogique
├── thermo_engine.py                    # Thermodynamique
├── models.py                           # ORM SQLAlchemy
├── requirements.txt                    # Dépendances Python
├── run.bat                             # (NEW) Script démarrage
│
├── templates/
│   ├── distillation_advanced.html      # Dashboard principal
│   ├── distillation_q_factor.html      # (NEW) Q-Factor module
│   └── ... (autres pages)
│
├── static/
│   ├── style.css                       # Styles
│   └── app.js                          # Scripts
│
├── thermo.db                           # Base SQLite (auto-créée)
│
├── DISTILLATION_MODULE_README.md       # (NEW) Documentation
├── TECHNICAL_SPECS.md                  # (NEW) Specs techniques
├── CHANGELOG.md                        # (NEW) Résumé changements
└── integration_test.py                 # (NEW) Test pipeline
```

---

## ⚙️ Configuration

### Port Application
Par défaut: **5000**

Pour changer, éditer **app.py** (dernière ligne) :
```python
app.run(debug=True, port=5001)  # Port 5001 au lieu de 5000
```

### Base de Données
SQLite auto-créée: **thermo.db**

Pour réinitialiser:
```bash
rm thermo.db
python app.py
```

---

## 🔧 Dépannage

### "Python not found"
```bash
# Sur Windows, utiliser le chemin complet :
C:\Users\[YourUsername]\AppData\Local\Programs\Python\Python310\python.exe --version
```

### "Module not found: flask"
```bash
# Réinstaller dépendances :
pip install --upgrade pip
pip install -r requirements.txt
```

### "Port 5000 already in use"
```bash
# Tuer le processus Python :
# Windows:
taskkill /IM python.exe /F

# Mac/Linux:
pkill python
```

### Application très lente
```bash
# Redémarrer Flask sans mode debug :
# Éditer app.py:
app.run(debug=False, port=5000)
```

---

## 📚 Documentation Complète

- **README:** DISTILLATION_MODULE_README.md
- **Spécifications techniques:** TECHNICAL_SPECS.md
- **Historique changements:** CHANGELOG.md

---

## 🎯 Premiers Pas

### 1. Installation (< 1 min)
```bash
run.bat
```

### 2. Tester Simulation (< 1 min)
Accéder à http://localhost:5000/distillation_advanced
Cliquer "Simuler" avec les paramètres par défaut

### 3. Explorer Q-Factor (< 2 min)
Accéder à http://localhost:5000/distillation_q_factor
Sélectionner un état thermique
Observer la q-line mise à jour

### 4. Utiliser API (< 5 min)
```bash
curl -X POST http://localhost:5000/api/distillation/full_simulation \
  -H "Content-Type: application/json" \
  -d '{"comp1_id": 6, "comp2_id": 5, "F_flow": 100, ...}'
```

---

## 📞 Support

Pour toute question ou problème :
1. Consulter le README : DISTILLATION_MODULE_README.md
2. Vérifier les specs techniques : TECHNICAL_SPECS.md
3. Exécuter les tests : integration_test.py

---

## ✅ Checklist Démarrage

- [ ] Python 3.8+ installé
- [ ] Dépendances installées (`pip install -r requirements.txt`)
- [ ] Tests passent (`python integration_test.py`)
- [ ] Application démarre (`python app.py`)
- [ ] Navigateur ouvre http://localhost:5000
- [ ] Simulation teste correctement

---

**Application prête pour la production !** ✅

*Version 2.0.0 - Module Distillation Avancée*
*Dernière mise à jour: 2024-05-22*
