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

## Relecture de crise

Un instantané de la situation est conservé toutes les **30 secondes** dans `crisis_snapshots` (rétention **24 heures**). Le bouton « Relecture de crise » ouvre une vue indépendante en lecture seule : risques, statuts des infrastructures et de la flotte, incidents et missions observés. L'API `GET /replay` liste les captures (pagination `before` possible), `GET /replay/{id}` renvoie un instantané.

Ces archives ne reconstruisent **pas** la période antérieure à leur activation ; les scores passés ne sont jamais recalculés avec le graphe actuel. MongoDB et Neo4j sont lus successivement dans une courte fenêtre, pas dans une transaction commune. La carte utilise la géométrie de référence actuelle, mais les statuts et scores enregistrés. L'archive n'exécute aucune action sur la crise vivante.

## Centre de notifications

Les incidents, appels et arrivées/blocages de mission créent des alertes conservées dans MongoDB (`notifications`). Chaque alerte affiche le lieu, l'heure, la source, la gravité et l'état **à traiter / pris en compte / résolu**. La prise en compte par un opérateur ne résout pas l'incident : elle enregistre uniquement qui a vu l'alerte. Les incidents résolus passent automatiquement à « résolu ». Les événements encore actifs et les appels en attente sont retrouvés au démarrage ; l'historique clos n'est pas transformé en nouvelles alertes. La console actualise la boîte toutes les six secondes. En mode sécurisé, l'observateur peut lire mais pas acquitter.

Le bouton « Voir le lieu sur la carte » sélectionne le site, centre la carte et affiche l'origine et l'explication de l'alerte, sans l'acquitter ni modifier l'incident. Pour un incident ouvert, l'impact potentiel est calculé en lecture seule sur l'état actuel : les sites estimés apparaissent en pointillés, distincts du fait enregistré. Un incident clos ne reçoit pas de nouvelle estimation courante. Cette estimation n'est ni un dommage constaté ni une mutation de la crise.
Les signaux des nouvelles urgences sont dédupliqués par identifiant de notification dans le stockage local du navigateur, y compris après rechargement. Au premier accès, les alertes déjà présentes sont affichées sans son ; ensuite, les alertes nouvelles pendant une déconnexion sont signalées à la reprise. Les alertes non urgentes restent silencieuses. En cas de stockage local désactivé, ce suivi ne survit pas à un rechargement ; l'affichage des notifications en base reste disponible. Le navigateur peut également bloquer la lecture audio automatique.

## Fraîcheur des sources

La console affiche, pour les appels CACU, la voirie, SIEM, SCADA, les quatre zones Open-Meteo et les mises à jour de flotte d'agence, la dernière **donnée reçue**. `GET /integration/sources` lit ces horodatages depuis MongoDB sans écrire d'incident. La météo, interrogée périodiquement, est marquée « mesure en retard » au-delà de quatre minutes ; une réponse météo vide n'est pas une mesure. Les autres flux événementiels peuvent rester silencieux sans être en panne : au-delà de trente minutes, « silence prolongé » ne conclut pas à une défaillance. Une pause du simulateur et un générateur arrêté sont signalés séparément ; une mise à jour de flotte calculée localement ne se fait pas passer pour une réception d'agence. Ce suivi n'est pas une supervision réseau de fournisseurs réels.

## Priorité de lecture des notifications

Les alertes « à traiter » sont classées dans la console par un score **calculé à l'affichage** : gravité enregistrée, ancienneté et hôpital ciblé ou potentiellement concerné selon le modèle de risque actuel. La mention P1/P2/P3 est une aide à la lecture, pas une gravité constatée ni une instruction d'intervention ; elle ne modifie ni MongoDB ni l'état d'un incident. Les alertes prises en compte ou résolues restent triées chronologiquement. La liste est bornée aux 500 dernières alertes de l'état choisi ; si elle est tronquée, la console le signale.

## Vérification

Pour les tests, installer `backend/requirements-dev.txt`. Depuis `backend` : `python -m unittest discover -s tests -v`. Depuis `frontend` : `npm test` puis `npm run build`. Les parcours HTTP isolés utilisent Mongo en mémoire et un graphe routier contrôlé : ils vérifient appel → mission → arrivée → retour à base et incident → projection → résolution → historique sans modifier les bases de la simulation en cours. Les tests couvrent aussi les accès anonymes, les rôles, la clé d'agence et l'échappement des textes de la carte.

## Étapes vers un prototype de production complet

- Scénarios de crise **reproductibles** avec paramètres et amorce aléatoire contrôlés ; la relecture temporelle observée est livrée, mais n'est pas un moteur de rejeu déterministe des événements.
- Parcours HTTP isolés livrés ; encore nécessaires : tests de bout en bout sur de vraies bases isolées, charge, pannes MongoDB/Neo4j et mesures de latence avec objectifs chiffrés.
- Validation métier des dépendances et des scores de risques ; justification et incertitude explicites dans chaque recommandation.
- Sauvegarde/restauration vérifiées, migrations, rétention des journaux, supervision et déploiement HTTPS reproductible.
- Revue de sécurité et exercices opérateur avant toute utilisation hors du cadre de simulation.

**Aucun de ces points futurs n'est présenté comme déjà livré.**
