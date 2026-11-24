# Vigie Urbaine

Vigie Urbaine est un simulateur académique de crises urbaines pour le Grand Tunis. Sa console cartographique permet de suivre un incident, de comprendre les risques qu’il fait peser sur les infrastructures et d’observer la réponse simulée, par exemple le changement d’itinéraire d’une ambulance lorsqu’une route est bloquée.

## Ce que montre la démo

| Fonction | Ce que l’on peut observer |
| --- | --- |
| Carte des infrastructures | Recherche par nom, identifiant ou type. La fiche d’un site expose les facteurs du score de risque. |
| Incidents et risques | Propagation selon les dépendances du graphe, alertes et recommandations d’intervention. |
| Projection What-if | Estimation des sites potentiellement concernés, des chaînes de dépendance et de l’incertitude, sans écriture dans les bases. |
| Missions SAMU | Appel, affectation d’une ambulance, progression, détour et retour à la base. |
| Relecture | Consultation d’instantanés de la crise collectés pendant le flux automatique, toutes les 30 secondes et conservés 24 heures. |

## Architecture

| Composant | Rôle |
| --- | --- |
| React, Vite et Leaflet | Console opérateur, carte OpenStreetMap et relecture. |
| FastAPI | API des incidents, projections, alertes, missions et commandes de simulation. Vite transmet les requêtes `/api` au backend. |
| Neo4j | Infrastructures, dépendances, routes et coûts de parcours. Le graphe initial est fourni dans [data/seed.cypher](data/seed.cypher). |
| MongoDB | Incidents, appels, missions, flotte, notifications, historiques et sessions. |

## Démarrage local

Installer Docker avec Compose, Python 3.11 ou plus récent, et Node.js 22.12 ou plus récent. Les commandes ci-dessous utilisent PowerShell.

**1. Démarrer les bases depuis la racine du dépôt.**

```powershell
docker compose -f docker-compose.fresh.yml up -d --wait
docker compose -f docker-compose.fresh.yml exec -T neo4j cypher-shell -u neo4j -p urbanbutterfly -f /seed.cypher
```

Importer le seed à la première initialisation. Cette configuration utilise des volumes distincts de ceux de `docker-compose.yml`. Pour arrêter les bases en conservant les données, utiliser `docker compose -f docker-compose.fresh.yml stop`.

**2. Créer un fichier `backend/.env`** avec les valeurs de la démo locale.

```dotenv
NEO4J_URI=bolt://127.0.0.1:7688
NEO4J_USER=neo4j
NEO4J_PASSWORD=urbanbutterfly
MONGO_URI=mongodb://admin:urbanbutterfly@127.0.0.1:27018
MONGO_DB=urban_butterfly_clean
SECURITY_MODE=demo
```

**3. Lancer l’API dans un terminal.**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**4. Lancer la console dans un second terminal, depuis la racine.**

```powershell
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Ouvrir la [console](http://127.0.0.1:5173), la [documentation interactive de l’API](http://127.0.0.1:8000/docs) ou le [contrôle de santé](http://127.0.0.1:8000/health).

## Trois façons de faire la démonstration

### Projection sur la carte

1. Activer **Mode Simulation** dans la console.
2. Rechercher et sélectionner le poste électrique `P1`.
3. Choisir la panne électrique. Cliquer sur un site surligné pour voir la chaîne de dépendance et les facteurs de son score.

### Appel SAMU et détour manuel

Depuis `backend`, avec l’API démarrée, utiliser [le script de simulation](backend/scripts/simulation.py). Cette démonstration enregistre les actions dans les bases locales. La mission manuelle avance même si le flux automatique est arrêté.

```powershell
.\.venv\Scripts\python.exe scripts\simulation.py appel H3
.\.venv\Scripts\python.exe scripts\simulation.py missions
.\.venv\Scripts\python.exe scripts\simulation.py detours M-01
.\.venv\Scripts\python.exe scripts\simulation.py incident route R3
.\.venv\Scripts\python.exe scripts\simulation.py comparer M-01
.\.venv\Scripts\python.exe scripts\simulation.py court M-01
.\.venv\Scripts\python.exe scripts\simulation.py resoudre ID_INCIDENT
```

Remplacer `M-01` par l’identifiant affiché, `R3` par une route proposée par `detours` et `ID_INCIDENT` par l’identifiant du blocage. La mission doit être encore en route pendant le test. Pour les autres commandes, utiliser `scripts\simulation.py --help`. En mode sécurisé, placer `--connexion` avant la sous-commande.

### Flux automatique et scénario guidé

Le flux démarre sur action explicite. Depuis la [documentation interactive](http://127.0.0.1:8000/docs), appeler `POST /integration/stream` avec `{"action":"start"}`. Le premier appel automatique survient après 35 à 90 secondes et le premier incident après 110 à 240 secondes. L’action `stop` arrête le flux et l’enregistrement des instantanés.

Pendant que le flux tourne sur une instance de démo, `POST /integration/scenario` permet d’avancer pas à pas avec les actions `rain`, `ambulance`, `block` et `power`. Le blocage demande une mission en cours et une route avec un détour possible. `GET /integration/scenario` affiche la progression, `GET /integration/sources` la fraîcheur des canaux et `GET /integration/activity` le journal.

## Tests

Depuis `backend` :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Depuis `frontend` :

```powershell
npm ci
npm test
npm run build
```

Les tests backend des parcours HTTP utilisent un MongoDB en mémoire et un graphe contrôlé. Ils couvrent notamment l’affectation de la flotte, le reroutage, la résolution, l’historique et les droits d’accès.

## Hypothèses et limites

- Les risques et recommandations sont des estimations du modèle. Une pluie indique une exposition possible et une route bloquée peut réduire l’accès à un site ou retarder son approvisionnement.
- Les itinéraires restent indicatifs. La console signale les liaisons douteuses et indique la provenance du tracé. Le détour via R28 comporte quatre arcs orientés issus de trajets OpenStreetMap calculés par OSRM. Le reste du réseau nécessite une validation géographique. Voir [l’audit routier](docs/audit-graphe.md).
- La relecture restitue les instantanés disponibles. Une exploitation au-delà de la démo requiert des tests sur bases réelles, une validation métier, la supervision et des sauvegardes vérifiées.

## Mode sécurisé

Réserver le mode `demo` à la machine locale. Pour activer les rôles, définir `SECURITY_MODE=secure`, `AUTH_OPERATOR_PASSWORD` (14 caractères minimum), `AUTH_AGENCY_KEY` (32 minimum) et, si nécessaire, `AUTH_VIEWER_PASSWORD` (14 minimum). L’opérateur gère les incidents et les missions. L’observateur consulte la situation et peut lancer une projection. Les intégrations d’agences utilisent `X-Agency-Key` pour les appels et les mises à jour de flotte.

Docker Compose lit les mots de passe des bases depuis le `.env` de la racine. FastAPI lit ses paramètres depuis `backend/.env`. Sur un volume existant, changer les mots de passe dans les bases elles-mêmes. Pour un accès réseau, servir le frontend et `/api` derrière un proxy HTTPS de même origine, configurer `AUTH_COOKIE_SECURE=true` et `AUTH_ALLOWED_ORIGINS`, puis réserver les ports des services au réseau interne. Les fichiers locaux contenant des secrets sont ignorés par Git.
