# Urban Butterfly — simulateur de crises urbaines en cascade

Console tactique académique pour le Grand Tunis. Les appels, agences, missions et incidents sont **simulés** ; les projections sont des estimations, pas des décisions opérationnelles ou des prévisions garanties.

## Démarrage local

Prérequis : Docker, Python et Node.js. Copier `.env.example` vers `backend/.env`, puis démarrer les bases avec `docker compose up -d`. Installer `backend/requirements.txt`, démarrer `uvicorn app.main:app --host 127.0.0.1 --port 8000` depuis `backend`, puis `npm ci` et `npm run dev` depuis `frontend`. L'interface est sur `http://localhost:5173`.

`SECURITY_MODE=demo` conserve l'accès local non authentifié pour l'enseignement. **Ne jamais rendre l'API, Vite ou les bases accessibles depuis Internet dans ce mode.** Les ports des bases sont limités à `127.0.0.1` par défaut.

## Mode simulation sécurisée

1. Définir `MONGO_PASSWORD` et `NEO4J_PASSWORD` dans un `.env` **à la racine** (lu par Docker Compose), puis modifier les URI correspondantes dans `backend/.env` (lu par FastAPI). Pour des volumes Docker déjà initialisés, changer le mot de passe **dans la base existante** : modifier la variable Compose seule ne réinitialise pas les identifiants. Ne pas supprimer les volumes contenant des incidents.
2. Définir `SECURITY_MODE=secure`, `AUTH_OPERATOR_PASSWORD` (14 caractères minimum), `AUTH_AGENCY_KEY` (32 minimum) et éventuellement `AUTH_VIEWER_PASSWORD` (14 minimum). Générer des secrets aléatoires hors du dépôt.
3. Se connecter avec `operateur` ou `observateur`. L'observateur lit la situation et peut faire des projections, mais ne modifie ni incidents ni missions. Les intégrations externes POST `/integration/calls` et POST `/integration/fleet-updates` acceptent `X-Agency-Key`; cette clé n'ouvre pas la console. Les autres mutations exigent une session opérateur.
4. Pour un accès réseau, mettre un reverse proxy HTTPS devant le frontend et l'API **sous la même origine** (`/api` vers l'API, en retirant le préfixe), définir `AUTH_COOKIE_SECURE=true` et `AUTH_ALLOWED_ORIGINS=https://votre-domaine`, puis bloquer l'accès direct à l'API, Vite et aux bases. La configuration locale ne constitue pas à elle seule un déploiement Internet sécurisé.

Les sessions expirent au bout de huit heures et sont invalidées à la déconnexion. Les actions HTTP en mode sécurisé sont enregistrées dans `audit_log` (acteur, chemin, date, code de réponse ; aucun corps ni mot de passe). Les journaux restent à sauvegarder et à protéger. Les tentatives de connexion sont temporairement limitées. L'API `/health` est publique et ne révèle que l'état des services.

## Vérification

Depuis `backend` : `python -m unittest discover -s tests -v`. Depuis `frontend` : `npm run build`. Les tests de sécurité vérifient notamment les accès anonymes, les rôles, l'origine des mutations et la clé d'agence.

## Étapes vers un prototype de production complet

- Scénarios de crise **reproductibles** et relecture temporelle séparée de l'état courant ; jamais de projection qui modifie la ville.
- Parcours complets automatisés, tests de charge, pannes de MongoDB/Neo4j et mesures de latence avec objectifs chiffrés.
- Validation métier des dépendances et des scores de risques ; justification et incertitude explicites dans chaque recommandation.
- Sauvegarde/restauration vérifiées, migrations, rétention des journaux, supervision et déploiement HTTPS reproductible.
- Revue de sécurité et exercices opérateur avant toute utilisation hors du cadre de simulation.

**Aucun de ces points futurs n'est présenté comme déjà livré.**
