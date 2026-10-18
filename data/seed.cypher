// =============================================
// URBAN BUTTERFLY - Graphe minimal (MVP, section 24)
// 2 zones, 2 postes, 2 antennes, 2 hopitaux, 3 routes, 1 depot
// =============================================

// Contraintes d'unicite (mal bonne pratique Neo4j : un id -> un noeud)
CREATE CONSTRAINT infra_id IF NOT EXISTS
FOR (n:Infrastructure) REQUIRE n.id IS UNIQUE;

// ---------- ZONES ----------
MERGE (zc:Zone:Infrastructure {id: 'Z1', kind: 'Zone', name: 'Tunis Centre', lat: 36.80, lon: 10.18})
MERGE (zn:Zone:Infrastructure {id: 'Z2', kind: 'Zone', name: 'Tunis Nord',  lat: 36.86, lon: 10.16});

// ---------- POSTES ELECTRIQUES ----------
MERGE (p1:PowerStation:Infrastructure {id: 'P1', kind: 'PowerStation', name: 'Poste Sud',    lat: 36.79, lon: 10.19, capacity_mw: 120, status: 'ONLINE'})
MERGE (p2:PowerStation:Infrastructure {id: 'P2', kind: 'PowerStation', name: 'Poste Nord',    lat: 36.87, lon: 10.17, capacity_mw: 150, status: 'ONLINE'});

// ---------- ANTENNES TELECOM ----------
MERGE (t1:TelecomTower:Infrastructure {id: 'T1', kind: 'TelecomTower', name: 'Antenne Centre', lat: 36.805, lon: 10.185, coverage_km: 3, status: 'ONLINE'})
MERGE (t2:TelecomTower:Infrastructure {id: 'T2', kind: 'TelecomTower', name: 'Antenne Nord',   lat: 36.865, lon: 10.165, coverage_km: 4, status: 'ONLINE'});

// ---------- HOPITAUX ----------
MERGE (h1:Hospital:Infrastructure {id: 'H1', kind: 'Hospital', name: 'Hopital Charles Nicolle', lat: 36.81, lon: 10.20, beds: 350, backup_power_hours: 0,  medicine_stock_days: 2, criticality: 5, status: 'OPERATIONAL'})
MERGE (h2:Hospital:Infrastructure {id: 'H2', kind: 'Hospital', name: 'Hopital Mongi Slim',      lat: 36.85, lon: 10.15, beds: 200, backup_power_hours: 6,  medicine_stock_days: 5, criticality: 3, status: 'OPERATIONAL'});

// ---------- ROUTES ----------
MERGE (r1:Road:Infrastructure {id: 'R1', kind: 'Road', name: 'Route H2 - Depot',    lat: 36.84, lon: 10.16, lanes: 2, length_km: 4.5, status: 'CLEAR'})
MERGE (r2:Road:Infrastructure {id: 'R2', kind: 'Road', name: 'Route W1 - H1',      lat: 36.81, lon: 10.19, lanes: 2, length_km: 2.0, status: 'CLEAR'})
MERGE (r3:Road:Infrastructure {id: 'R3', kind: 'Road', name: 'Avenue Habib Bourguiba', lat: 36.80, lon: 10.18, lanes: 4, length_km: 1.8, status: 'CLEAR'});

// ---------- DEPOT LOGISTIQUE ----------
MERGE (w1:Warehouse:Infrastructure {id: 'W1', kind: 'Warehouse', name: 'Depot Medical Sud', lat: 36.78, lon: 10.20, capacity_tons: 50, medicine_stock_days: 7, status: 'OPERATIONAL'});

// ---------- RELATIONS DE DEPENDANCE ----------
MATCH (t1 {id: 'T1'}), (p1 {id: 'P1'})
MERGE (t1)-[:DEPENDS_ON {reason: 'alimentation electrique'}]->(p1);

MATCH (t2 {id: 'T2'}), (p2 {id: 'P2'})
MERGE (t2)-[:DEPENDS_ON {reason: 'alimentation electrique'}]->(p2);

MATCH (h1 {id: 'H1'}), (p1 {id: 'P1'})
MERGE (h1)-[:DEPENDS_ON {reason: 'alimentation electrique, sans secours'}]->(p1);

MATCH (h2 {id: 'H2'}), (p2 {id: 'P2'})
MERGE (h2)-[:DEPENDS_ON {reason: 'alimentation electrique'}]->(p2);

// ---------- ACCESSIBILITE ROUTE ----------
MATCH (h1 {id: 'H1'}), (r2 {id: 'R2'})
MERGE (h1)-[:CONNECTED_BY {role: 'route principale'}]->(r2);

MATCH (h2 {id: 'H2'}), (r1 {id: 'R1'})
MERGE (h2)-[:CONNECTED_BY {role: 'route principale'}]->(r1);

MATCH (r1 {id: 'R1'}), (r3 {id: 'R3'})
MERGE (r1)-[:CONNECTED_BY {role: 'lien vers avenue principale'}]->(r3);

MATCH (w1 {id: 'W1'}), (r2 {id: 'R2'})
MERGE (w1)-[:CONNECTED_BY {role: 'route principale'}]->(r2);

MATCH (w1 {id: 'W1'}), (r3 {id: 'R3'})
MERGE (w1)-[:CONNECTED_BY {role: 'route de repli'}]->(r3);

// ---------- APPROVISIONNEMENT ----------
MATCH (h1 {id: 'H1'}), (w1 {id: 'W1'})
MERGE (h1)-[:SUPPLIED_BY {product: 'medicaments', base_days: 3}]->(w1);

MATCH (h2 {id: 'H2'}), (w1 {id: 'W1'})
MERGE (h2)-[:SUPPLIED_BY {product: 'medicaments', base_days: 5}]->(w1);

// ---------- LOCALISATION GEOGRAPHIQUE ----------
MATCH (n:Infrastructure), (z:Zone)
WHERE n.id IN ['H1','T1','W1','P1'] AND z.id = 'Z1'
MERGE (n)-[:LOCATED_IN]->(z);

MATCH (n:Infrastructure), (z:Zone)
WHERE n.id IN ['H2','T2','P2'] AND z.id = 'Z2'
MERGE (n)-[:LOCATED_IN]->(z);

MATCH (r1x:Road {id: 'R1'}), (z2x:Zone {id: 'Z2'})
MERGE (r1x)-[:LOCATED_IN]->(z2x);

MATCH (r2x:Road {id: 'R2'}), (z1x:Zone {id: 'Z1'})
MERGE (r2x)-[:LOCATED_IN]->(z1x);

MATCH (r3x:Road {id: 'R3'}), (z1x:Zone {id: 'Z1'})
MERGE (r3x)-[:LOCATED_IN]->(z1x);
