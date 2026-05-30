# Deploiement GitHub Pages

GitHub Pages ne lance pas Python/Flask. Ce depot contient donc un export
statique pour Pages : vitrine, selection et ecran de configuration en mode
demonstration.

Les comptes, calculs, sauvegardes, historique, emails et appels IA necessitent
toujours un hebergement backend Flask.

## Deploiement automatique

Le workflow `.github/workflows/deploy-pages.yml` genere le site statique dans
`site/` puis le publie sur GitHub Pages a chaque push sur `main`.

Etapes cote GitHub :

1. Pousser le code sur GitHub.
2. Ouvrir `Settings > Pages`.
3. Choisir `Build and deployment > Source: GitHub Actions`.
4. Relancer le workflow `Deploy static site to GitHub Pages` si besoin.

## Build local

```powershell
pip install -r requirements.txt
python build_static.py
```

Pour simuler le chemin d'un site projet GitHub Pages :

```powershell
$env:GITHUB_PAGES_BASE_PATH="/nom-du-repo"
python build_static.py
```
