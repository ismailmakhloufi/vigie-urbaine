# Audit du graphe routier chargé (lecture seule)

## Corrections appliquées au calcul des itinéraires

Sur l'instance auditée, R22–R5 est écartée du routage. Les quatre arcs orientés entre R22, R28 et R5 passent par des trajets automobiles calculés avec [OSRM](https://project-osrm.org/docs/) sur les données [OpenStreetMap © les contributeurs, ODbL](https://www.openstreetmap.org/copyright), via `routing.openstreetmap.de/routed-car`. Les ancrages d'origine et leurs écarts au réseau routable sont conservés dans `backend/app/services/osm_road_links.json`. Le point retenu pour R28 est à 21,5 m du réseau. Les distances calculées sont d'environ 13,3 km de R22 vers R28 et 10,7 km de R28 vers R5. Les distances inverses diffèrent car les trajets sont orientés. La géométrie OSRM est utilisée quand tous les arcs du trajet disposent de cette donnée.

Pour les autres arcs, lorsque la distance déclarée est inférieure de plus de 100 m au minimum mesuré entre les sommets des tracés, le moteur relève la distance à ce minimum et ajuste la durée selon la vitesse implicite du graphe. Cette borne reste une estimation à vol d'oiseau. Les arcs signalés demeurent visibles dans le comparateur et la continuité routière reste à valider. La correction est appliquée en mémoire et fonctionne avec les données existantes dans Neo4j.

Exécution locale du 22 novembre 2026 avec `backend/scripts/audit_graph.py` sur Neo4j, transactions `READ_ACCESS`. Pour reproduire depuis `backend` : `.venv/Scripts/python scripts/audit_graph.py` (sous Windows). Le rapport reflète **cette instance**, pas nécessairement une autre installation ou le seed seul. Aucune donnée persistante n'a été changée.

**Diagnostic, non validation terrain.** Certains tracés du seed sont décrits comme « GPS réels », mais aucune correspondance traçable entre les identifiants R1–R30, leurs segments et des identifiants de voies OSM n'est fournie. Les points de référence et coûts peuvent contredire les tracés. OpenStreetMap/Overpass peut servir de source indépendante de géométrie et d'intersections ([Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API), [attribution et licence ODbL](https://www.openstreetmap.org/copyright)), mais les noms, sens, ponts, accès et coordonnées doivent être rapprochés **voie par voie** avant correction. Une courte distance n'implique pas une connexion praticable ; une grande distance entre tracés peut aussi signaler un tracé incomplet ou mal associé.

**Priorité :** R22–R5 présente un écart minimal de 6,68 km pour 1,4 km déclaré. Cette arête est toujours utilisée par le routage, même si le frontend interrompt le dessin. Son retrait isolé laisse ici une composante unique via d'autres arêtes, mais change potentiellement les meilleurs trajets. R1–R9, R10–R26 et R17–R29 sont des liens-ponts dans ce graphe : les enlever sans remplacement sépare le réseau. Ne pas lancer `seed.cypher` comme une procédure de correction : il peut réinstaller les liens suspects.

**Prochaine validation :** relever pour chaque paire suspecte les identifiants OSM des voies, leur intersection ou liaison via voies intermédiaires, les restrictions de circulation et la date de l'extrait ; recalculer distances et temps sur le réseau vérifié ; tester la connectivité et les itinéraires SAMU/approvisionnement avant application d'une migration idempotente qui ne touche ni incidents, ni missions, ni archives. Les seuils de ce rapport servent seulement à prioriser la vérification.

30 routes ; 47 paires CONNECTS_TO ; 21 liens CONNECTED_BY site→route ; 1 composante(s) routière(s).
Distances minimales à vol d'oiseau entre sommets des tracés ; un faible écart ne prouve **pas** une jonction (pont, sens, accès). Seuil de tri indicatif : 1 km.

## CONNECTS_TO à examiner (écart > 1 km ou métrique déclarée inférieure à l'écart)

| Lien | Écart tracés km | Coût déclaré km | Alerte | Sans ce lien |
|---|---:|---:|---|---|
| R1–R4 | 16.09 | 2.0 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R13–R4 | 15.25 | 1.5 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R1–R9 | 14.42 | 3.0 | écart important, coût < distance directe | 2 composantes |
| R20–R4 | 13.78 | 2.2 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R2–R23 | 12.07 | 1.0 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R3–R4 | 10.29 | 2.2 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R12–R4 | 9.06 | 1.8 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R2–R5 | 8.69 | 2.8 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R24–R5 | 8.39 | 3.0 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R13–R14 | 8.25 | 2.8 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R24–R29 | 8.16 | 1.6 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R16–R2 | 7.24 | 1.6 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R23–R6 | 7.18 | 0.6 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R12–R13 | 7.13 | 1.2 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R27–R8 | 6.94 | 1.0 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R22–R5 | 6.68 | 1.4 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R10–R26 | 6.12 | 1.3 | écart important, coût < distance directe | 2 composantes |
| R15–R18 | 5.72 | 1.4 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R3–R5 | 5.56 | 3.8 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R2–R7 | 5.31 | 1.0 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R27–R30 | 5.28 | 0.8 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R2–R8 | 4.89 | 1.8 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R2–R6 | 4.67 | 0.7 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R27–R3 | 4.61 | 1.9 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R2–R21 | 4.39 | 1.2 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R28–R5 | 3.66 | 1.6 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R3–R7 | 3.35 | 1.6 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R22–R28 | 3.34 | 1.9 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R17–R29 | 3.34 | 0.9 | écart important, coût < distance directe | 2 composantes |
| R15–R16 | 2.88 | 1.3 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R6–R7 | 2.71 | 1.1 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R10–R9 | 2.57 | 1.5 | écart important, coût < distance directe | 2 composantes |
| R11–R9 | 2.40 | 1.2 | écart important, coût < distance directe | 2 composantes |
| R3–R8 | 2.37 | 1.2 | écart important, coût < distance directe | détours possibles (non quantifiés) |
| R1–R5 | 2.36 | 3.4 | écart important | détours possibles (non quantifiés) |
| R2–R3 | 1.36 | 1.4 | écart important | détours possibles (non quantifiés) |
| R30–R8 | 1.12 | 1.1 | écart important | détours possibles (non quantifiés) |
| R14–R22 | 1.01 | 2.0 | écart important | détours possibles (non quantifiés) |
| R16–R19 | 1.00 | 1.1 | écart important | détours possibles (non quantifiés) |

39 paire(s) signalée(s) sur 47 ; les arêtes non listées ne sont pas pour autant validées.

## CONNECTED_BY site→route à examiner (> 1 km)

| Site | Route | Distance point→tracé km |
|---|---|---:|
| H2 | R12 | 17.08 |
| PH8 | R9 | 15.18 |
| PH5 | R12 | 9.69 |
| H3 | R12 | 9.00 |
| H1 | R7 | 4.42 |
| W1 | R3 | 4.36 |
| H4 | R15 | 3.59 |
| PH2 | R8 | 3.10 |
| W2 | R9 | 3.06 |
| H3 | R14 | 2.51 |
| W1 | R19 | 2.04 |
| PH4 | R11 | 1.88 |
| H1 | R3 | 1.39 |
| PH3 | R10 | 1.14 |
| W3 | R14 | 1.07 |
| H4 | R16 | 1.03 |

16 lien(s) signalé(s) sur 21. Les points des sites et tracés ne constituent pas des adresses vérifiées.
