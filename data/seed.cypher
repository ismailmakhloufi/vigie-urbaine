// ============================================================
// VIGIE URBAINE - Graphe v2 : ville MVP complete (section 19)
// 4 zones <- 5 postes - 10 antennes - 5 hopitaux - 30 routes
//               - 8 pharmacies - 3 depots
// Idempotent : rejouer ne duplique rien (MERGE + IF NOT EXISTS)
// ============================================================
// IMPORTANT :
// Ce graphe représente un prototype de mini-jumeau numérique du Grand Tunis.
// Les noms/zones servent de repères géographiques, mais les dépendances
// électriques, télécom, logistiques, niveaux de criticité, stocks et secours
// sont des données SYNTHÉTIQUES conçues pour la simulation académique.
// Elles ne décrivent pas l'architecture opérationnelle réelle de Tunis.
// ============================================================


CREATE CONSTRAINT infra_id IF NOT EXISTS
FOR (n:Infrastructure) REQUIRE n.id IS UNIQUE;

// ---------- ZONES (4) ----------
MERGE (z1:Zone:Infrastructure {id:'Z1', kind:'Zone', name:'Tunis Centre',  lat:36.80, lon:10.18, status:'ONLINE'})
MERGE (z2:Zone:Infrastructure {id:'Z2', kind:'Zone', name:'La Marsa',      lat:36.87, lon:10.30, status:'ONLINE'})
MERGE (z3:Zone:Infrastructure {id:'Z3', kind:'Zone', name:'L ARIANA',      lat:36.86, lon:10.20, status:'ONLINE'})
MERGE (z4:Zone:Infrastructure {id:'Z4', kind:'Zone', name:'Ben Arous',     lat:36.75, lon:10.23, status:'ONLINE'});

// ---------- POSTES ELECTRIQUES (5) ----------
MERGE (p1:PowerStation:Infrastructure {id:'P1', kind:'PowerStation', name:'Poste Sud',        lat:36.79, lon:10.19, capacity_mw:120, status:'ONLINE', criticality:3})
MERGE (p2:PowerStation:Infrastructure {id:'P2', kind:'PowerStation', name:'Poste Nord',       lat:36.87, lon:10.17, capacity_mw:150, status:'ONLINE', criticality:3})
MERGE (p3:PowerStation:Infrastructure {id:'P3', kind:'PowerStation', name:'Poste Ariana',     lat:36.84, lon:10.23, capacity_mw:130, status:'ONLINE', criticality:4})
MERGE (p4:PowerStation:Infrastructure {id:'P4', kind:'PowerStation', name:'Poste Ben Arous',  lat:36.74, lon:10.22, capacity_mw:110, status:'ONLINE', criticality:4})
MERGE (p5:PowerStation:Infrastructure {id:'P5', kind:'PowerStation', name:'Poste Est',        lat:36.82, lon:10.25, capacity_mw:140, status:'ONLINE', criticality:5});

// ---------- ANTENNES TELECOM (10) ----------
MERGE (t1:TelecomTower:Infrastructure {id:'T1',  kind:'TelecomTower', name:'Antenne Centre',   lat:36.802, lon:10.182, coverage_km:3, status:'ONLINE'})
MERGE (t2:TelecomTower:Infrastructure {id:'T2',  kind:'TelecomTower', name:'Antenne Nord',     lat:36.868, lon:10.171, coverage_km:4, status:'ONLINE'})
MERGE (t3:TelecomTower:Infrastructure {id:'T3',  kind:'TelecomTower', name:'Antenne Ariana',   lat:36.855, lon:10.212, coverage_km:3, status:'ONLINE'})
MERGE (t4:TelecomTower:Infrastructure {id:'T4',  kind:'TelecomTower', name:'Antenne Ben Arous',lat:36.745, lon:10.222, coverage_km:3, status:'ONLINE'})
MERGE (t5:TelecomTower:Infrastructure {id:'T5',  kind:'TelecomTower', name:'Antenne Est',      lat:36.818, lon:10.252, coverage_km:4, status:'ONLINE'})
MERGE (t6:TelecomTower:Infrastructure {id:'T6',  kind:'TelecomTower', name:'Antenne Medina',   lat:36.833, lon:10.194, coverage_km:2, status:'ONLINE'})
MERGE (t7:TelecomTower:Infrastructure {id:'T7',  kind:'TelecomTower', name:'Antenne Gammarth', lat:36.881, lon:10.289, coverage_km:4, status:'ONLINE'})
MERGE (t8:TelecomTower:Infrastructure {id:'T8',  kind:'TelecomTower', name:'Antenne Sud',      lat:36.773, lon:10.192, coverage_km:3, status:'ONLINE'})
MERGE (t9:TelecomTower:Infrastructure {id:'T9',  kind:'TelecomTower', name:'Antenne Ouest',    lat:36.762, lon:10.245, coverage_km:3, status:'ONLINE'})
MERGE (t10:TelecomTower:Infrastructure {id:'T10', kind:'TelecomTower', name:'Antenne Lac',     lat:36.901, lon:10.219, coverage_km:4, status:'ONLINE'});

// ---------- HOPITAUX (5) ----------
MERGE (h1:Hospital:Infrastructure {id:'H1', kind:'Hospital', name:'Hopital Charles Nicolle',  lat:36.81,  lon:10.20, beds:350, backup_power_hours:0, medicine_stock_days:2, criticality:5, status:'OPERATIONAL'})
MERGE (h2:Hospital:Infrastructure {id:'H2', kind:'Hospital', name:'Hopital Abderrahmen Mami', lat:36.87,  lon:10.30, beds:200, backup_power_hours:6, medicine_stock_days:5, criticality:3, status:'OPERATIONAL'})
MERGE (h3:Hospital:Infrastructure {id:'H3', kind:'Hospital', name:'Hopital Mahmoud Matri',    lat:36.852, lon:10.212, beds:250, backup_power_hours:4, medicine_stock_days:4, criticality:4, status:'OPERATIONAL'})
MERGE (h4:Hospital:Infrastructure {id:'H4', kind:'Hospital', name:'Hopital Habib Thameur',    lat:36.79,  lon:10.222, beds:180, backup_power_hours:0, medicine_stock_days:2, criticality:5, status:'OPERATIONAL'})
MERGE (h5:Hospital:Infrastructure {id:'H5', kind:'Hospital', name:'Hopital Fattouma Bourguiba', lat:36.74, lon:10.21, beds:150, backup_power_hours:3, medicine_stock_days:3, criticality:4, status:'OPERATIONAL'});

// ---------- ROUTES (30) : R1-R5 arteres, R6-R30 de quartier ----------
MERGE (r1:Road:Infrastructure  {id:'R1',  kind:'Road', name:'Autoroute A1 Nord',        lat:36.835, lon:10.180, status:'CLEAR'})
MERGE (r2:Road:Infrastructure  {id:'R2',  kind:'Road', name:'Avenue Habib Bourguiba',   lat:36.800, lon:10.180, status:'CLEAR'})
MERGE (r3:Road:Infrastructure  {id:'R3',  kind:'Road', name:'Route Tenor',              lat:36.790, lon:10.210, status:'CLEAR'})
MERGE (r4:Road:Infrastructure  {id:'R4',  kind:'Road', name:'Autoroute A4 Nord-Ouest',  lat:36.865, lon:10.195, status:'CLEAR'})
MERGE (r5:Road:Infrastructure  {id:'R5',  kind:'Road', name:'Perephamerique Sud-Est',   lat:36.805, lon:10.240, status:'CLEAR'})
MERGE (r6:Road:Infrastructure  {id:'R6',  kind:'Road', name:'Rue de Marseille',         lat:36.803, lon:10.187, status:'CLEAR'})
MERGE (r7:Road:Infrastructure  {id:'R7',  kind:'Road', name:'Avenue de la Liberte',     lat:36.808, lon:10.195, status:'CLEAR'})
MERGE (r8:Road:Infrastructure  {id:'R8',  kind:'Road', name:'Rue Bab Saadoun',          lat:36.812, lon:10.205, status:'CLEAR'})
MERGE (r9:Road:Infrastructure  {id:'R9',  kind:'Road', name:'Route de Gammarth',        lat:36.870, lon:10.250, status:'CLEAR'})
MERGE (r10:Road:Infrastructure {id:'R10', kind:'Road', name:'Avenue Habib Bourguiba Marsa',  lat:36.870, lon:10.300, status:'CLEAR'})
MERGE (r11:Road:Infrastructure {id:'R11', kind:'Road', name:'Rue Sidi Daoued',          lat:36.865, lon:10.290, status:'CLEAR'})
MERGE (r12:Road:Infrastructure {id:'R12', kind:'Road', name:'Avenue de la Republique',  lat:36.853, lon:10.208, status:'CLEAR'})
MERGE (r13:Road:Infrastructure {id:'R13', kind:'Road', name:'Rue Ibn Khaldoun',         lat:36.850, lon:10.218, status:'CLEAR'})
MERGE (r14:Road:Infrastructure {id:'R14', kind:'Road', name:'Route Ariana Lac',         lat:36.856, lon:10.240, status:'CLEAR'})
MERGE (r15:Road:Infrastructure {id:'R15', kind:'Road', name:'Rue Hedi Nouira',          lat:36.792, lon:10.218, status:'CLEAR'})
MERGE (r16:Road:Infrastructure {id:'R16', kind:'Road', name:'Rue Jellaz',               lat:36.786, lon:10.213, status:'CLEAR'})
MERGE (r17:Road:Infrastructure {id:'R17', kind:'Road', name:'Route Sidi Hassine',       lat:36.745, lon:10.215, status:'CLEAR'})
MERGE (r18:Road:Infrastructure {id:'R18', kind:'Road', name:'Rue Ibn Sina',             lat:36.796, lon:10.235, status:'CLEAR'})
MERGE (r19:Road:Infrastructure {id:'R19', kind:'Road', name:'Route de l Oued',          lat:36.785, lon:10.225, status:'CLEAR'})
MERGE (r20:Road:Infrastructure {id:'R20', kind:'Road', name:'Avenue Ariana Est',        lat:36.859, lon:10.245, status:'CLEAR'})
MERGE (r21:Road:Infrastructure {id:'R21', kind:'Road', name:'Rue Belgique',             lat:36.806, lon:10.172, status:'CLEAR'})
MERGE (r22:Road:Infrastructure {id:'R22', kind:'Road', name:'Boulevard du Lac',         lat:36.820, lon:10.250, status:'CLEAR'})
MERGE (r23:Road:Infrastructure {id:'R23', kind:'Road', name:'Rue Farhat Hached',        lat:36.798, lon:10.176, status:'CLEAR'})
MERGE (r24:Road:Infrastructure {id:'R24', kind:'Road', name:'Rue Ben Arous Centre',     lat:36.752, lon:10.230, status:'CLEAR'})
MERGE (r25:Road:Infrastructure {id:'R25', kind:'Road', name:'Avenue Mohamed V',         lat:36.810, lon:10.169, status:'CLEAR'})
MERGE (r26:Road:Infrastructure {id:'R26', kind:'Road', name:'Route Marsa Plage',        lat:36.878, lon:10.320, status:'CLEAR'})
MERGE (r27:Road:Infrastructure {id:'R27', kind:'Road', name:'Rue du Lac Turkana',       lat:36.815, lon:10.180, status:'CLEAR'})
MERGE (r28:Road:Infrastructure {id:'R28', kind:'Road', name:'Zone Industrielle',        lat:36.805, lon:10.248, status:'CLEAR'})
MERGE (r29:Road:Infrastructure {id:'R29', kind:'Road', name:'Rue Ibn Abi Dhiaf',        lat:36.750, lon:10.220, status:'CLEAR'})
MERGE (r30:Road:Infrastructure {id:'R30', kind:'Road', name:'Avenue Hedi Cherif',       lat:36.815, lon:10.178, status:'CLEAR'});

// ---------- DEPOTS LOGISTIQUES (3) ----------
MERGE (w1:Warehouse:Infrastructure {id:'W1', kind:'Warehouse', name:'Depot Medical Sud',     lat:36.78, lon:10.20, capacity_tons:50, medicine_stock_days:7, status:'OPERATIONAL'})
MERGE (w2:Warehouse:Infrastructure {id:'W2', kind:'Warehouse', name:'Depot Nord Marsa',      lat:36.865, lon:10.280, capacity_tons:35, medicine_stock_days:5, status:'OPERATIONAL'})
MERGE (w3:Warehouse:Infrastructure {id:'W3', kind:'Warehouse', name:'Depot Ariana Est',      lat:36.850, lon:10.260, capacity_tons:40, medicine_stock_days:6, status:'OPERATIONAL'});

// ---------- PHARMACIES (8) ----------
MERGE (ph1:Pharmacy:Infrastructure  {id:'PH1', kind:'Pharmacy', name:'Pharmacie Centrale',      lat:36.805, lon:10.190, status:'OPERATIONAL', criticality:2})
MERGE (ph2:Pharmacy:Infrastructure  {id:'PH2', kind:'Pharmacy', name:'Pharmacie Bab Saadoun',   lat:36.812, lon:10.200, status:'OPERATIONAL', criticality:2})
MERGE (ph3:Pharmacy:Infrastructure  {id:'PH3', kind:'Pharmacy', name:'Pharmacie Marsa',         lat:36.870, lon:10.295, status:'OPERATIONAL', criticality:2})
MERGE (ph4:Pharmacy:Infrastructure  {id:'PH4', kind:'Pharmacy', name:'Pharmacie Sidi Daoued',   lat:36.866, lon:10.288, status:'OPERATIONAL', criticality:3})
MERGE (ph5:Pharmacy:Infrastructure  {id:'PH5', kind:'Pharmacy', name:'Pharmacie Ariana',        lat:36.852, lon:10.220, status:'OPERATIONAL', criticality:2})
MERGE (ph6:Pharmacy:Infrastructure  {id:'PH6', kind:'Pharmacy', name:'Pharmacie Jellaz',        lat:36.788, lon:10.212, status:'OPERATIONAL', criticality:3})
MERGE (ph7:Pharmacy:Infrastructure  {id:'PH7', kind:'Pharmacy', name:'Pharmacie Sidi Hassine',  lat:36.746, lon:10.216, status:'OPERATIONAL', criticality:3})
MERGE (ph8:Pharmacy:Infrastructure  {id:'PH8', kind:'Pharmacy', name:'Pharmacie El Mourouj',    lat:36.760, lon:10.238, status:'OPERATIONAL', criticality:2});

// ============================================================
// DEPENDANCES ELECTRIQUES (tiers de poste par geo)
// ============================================================
MATCH (h:Hospital {id:'H1'}), (p:PowerStation {id:'P1'}) MERGE (h)-[:DEPENDS_ON {reason:'alimentation electrique, sans secours'}]->(p);
MATCH (h:Hospital {id:'H2'}), (p:PowerStation {id:'P2'}) MERGE (h)-[:DEPENDS_ON {reason:'alimentation electrique'}]->(p);
MATCH (h:Hospital {id:'H3'}), (p:PowerStation {id:'P3'}) MERGE (h)-[:DEPENDS_ON {reason:'alimentation electrique'}]->(p);
MATCH (h:Hospital {id:'H4'}), (p:PowerStation {id:'P4'}) MERGE (h)-[:DEPENDS_ON {reason:'alimentation electrique, sans secours'}]->(p);
MATCH (h:Hospital {id:'H5'}), (p:PowerStation {id:'P5'}) MERGE (h)-[:DEPENDS_ON {reason:'alimentation electrique'}]->(p);

MATCH (t {id:'T1'}),  (p2:PowerStation {id:'P1'}) MERGE (t)-[:DEPENDS_ON {reason:'alimentation'}]->(p2);
MATCH (t {id:'T2'}),  (p2:PowerStation {id:'P2'}) MERGE (t)-[:DEPENDS_ON {reason:'alimentation'}]->(p2);
MATCH (t {id:'T3'}),  (p2:PowerStation {id:'P3'}) MERGE (t)-[:DEPENDS_ON {reason:'alimentation'}]->(p2);
MATCH (t {id:'T4'}),  (p2:PowerStation {id:'P4'}) MERGE (t)-[:DEPENDS_ON {reason:'alimentation'}]->(p2);
MATCH (t {id:'T5'}),  (p2:PowerStation {id:'P5'}) MERGE (t)-[:DEPENDS_ON {reason:'alimentation'}]->(p2);
MATCH (t {id:'T6'}),  (p2:PowerStation {id:'P1'}) MERGE (t)-[:DEPENDS_ON {reason:'alimentation'}]->(p2);
MATCH (t {id:'T7'}),  (p2:PowerStation {id:'P2'}) MERGE (t)-[:DEPENDS_ON {reason:'alimentation'}]->(p2);
MATCH (t {id:'T8'}),  (p2:PowerStation {id:'P4'}) MERGE (t)-[:DEPENDS_ON {reason:'alimentation'}]->(p2);
MATCH (t {id:'T9'}),  (p2:PowerStation {id:'P4'}) MERGE (t)-[:DEPENDS_ON {reason:'alimentation'}]->(p2);
MATCH (t {id:'T10'}), (p2:PowerStation {id:'P5'}) MERGE (t)-[:DEPENDS_ON {reason:'alimentation'}]->(p2);

// ============================================================
// ROUTES : connexion de quartier vers arteres
// ============================================================
MATCH (a:Road {id:'R6'}),  (b:Road {id:'R1'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R7'}),  (b:Road {id:'R1'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R8'}),  (b:Road {id:'R2'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R9'}),  (b:Road {id:'R4'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R10'}), (b:Road {id:'R1'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R11'}), (b:Road {id:'R4'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R12'}), (b:Road {id:'R2'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R13'}), (b:Road {id:'R2'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R14'}), (b:Road {id:'R4'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R15'}), (b:Road {id:'R3'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R16'}), (b:Road {id:'R3'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R17'}), (b:Road {id:'R3'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R18'}), (b:Road {id:'R5'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R19'}), (b:Road {id:'R3'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R20'}), (b:Road {id:'R4'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R21'}), (b:Road {id:'R1'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R22'}), (b:Road {id:'R5'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R23'}), (b:Road {id:'R1'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R24'}), (b:Road {id:'R3'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R25'}), (b:Road {id:'R1'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R26'}), (b:Road {id:'R9'}) MERGE (a)-[:CONNECTED_BY {role:'route côtière'}]->(b);
MATCH (a:Road {id:'R27'}), (b:Road {id:'R1'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R28'}), (b:Road {id:'R5'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R29'}), (b:Road {id:'R3'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);
MATCH (a:Road {id:'R30'}), (b:Road {id:'R2'}) MERGE (a)-[:CONNECTED_BY {role:'artère'}]->(b);

// enrichissement : artères reliées entre elles (ronds-points du réseau)
MATCH (a:Road {id:'R1'}), (b:Road {id:'R2'}) MERGE (a)-[:CONNECTED_BY {role:'jonction centre'}]->(b);
MATCH (a:Road {id:'R2'}), (b:Road {id:'R3'}) MERGE (a)-[:CONNECTED_BY {role:'jonction sud'}]->(b);
MATCH (a:Road {id:'R4'}), (b:Road {id:'R1'}) MERGE (a)-[:CONNECTED_BY {role:'jonction nord'}]->(b);
MATCH (a:Road {id:'R5'}), (b:Road {id:'R3'}) MERGE (a)-[:CONNECTED_BY {role:'jonction sud-est'}]->(b);

// ============================================================
// ACCESSIBILITE des sites par leurs routes
// ============================================================
MATCH (h {id:'H1'}),  (r:Road {id:'R7'})  MERGE (h)-[:CONNECTED_BY {role:'principale'}]->(r);
MATCH (h {id:'H1'}),  (r:Road {id:'R3'})  MERGE (h)-[:CONNECTED_BY {role:'de secours'}]->(r);
MATCH (h {id:'H2'}),  (r:Road {id:'R10'}) MERGE (h)-[:CONNECTED_BY {role:'principale'}]->(r);
MATCH (h {id:'H2'}),  (r:Road {id:'R12'}) MERGE (h)-[:CONNECTED_BY {role:'de secours'}]->(r);
MATCH (h {id:'H3'}),  (r:Road {id:'R12'}) MERGE (h)-[:CONNECTED_BY {role:'principale'}]->(r);
MATCH (h {id:'H3'}),  (r:Road {id:'R14'}) MERGE (h)-[:CONNECTED_BY {role:'de secours'}]->(r);
MATCH (h {id:'H4'}),  (r:Road {id:'R15'}) MERGE (h)-[:CONNECTED_BY {role:'principale'}]->(r);
MATCH (h {id:'H4'}),  (r:Road {id:'R16'}) MERGE (h)-[:CONNECTED_BY {role:'de secours'}]->(r);
MATCH (h {id:'H5'}),  (r:Road {id:'R17'}) MERGE (h)-[:CONNECTED_BY {role:'principale'}]->(r);

MATCH (w {id:'W1'}),  (r:Road {id:'R3'})   MERGE (w)-[:CONNECTED_BY {role:'stock'}]->(r);
MATCH (w {id:'W1'}),  (r:Road {id:'R19'})  MERGE (w)-[:CONNECTED_BY {role:'stock'}]->(r);
MATCH (w {id:'W2'}),  (r:Road {id:'R9'})   MERGE (w)-[:CONNECTED_BY {role:'stock'}]->(r);
MATCH (w {id:'W3'}),  (r:Road {id:'R14'})  MERGE (w)-[:CONNECTED_BY {role:'stock'}]->(r);

MATCH (ph{id:'PH1'}), (r:Road {id:'R6'})   MERGE (ph)-[:CONNECTED_BY]->(r);
MATCH (ph{id:'PH2'}), (r:Road {id:'R8'})   MERGE (ph)-[:CONNECTED_BY]->(r);
MATCH (ph{id:'PH3'}), (r:Road {id:'R10'})  MERGE (ph)-[:CONNECTED_BY]->(r);
MATCH (ph{id:'PH4'}), (r:Road {id:'R11'})  MERGE (ph)-[:CONNECTED_BY]->(r);
MATCH (ph{id:'PH5'}), (r:Road {id:'R12'})  MERGE (ph)-[:CONNECTED_BY]->(r);
MATCH (ph{id:'PH6'}), (r:Road {id:'R16'})  MERGE (ph)-[:CONNECTED_BY]->(r);
MATCH (ph{id:'PH7'}), (r:Road {id:'R17'})  MERGE (ph)-[:CONNECTED_BY]->(r);
MATCH (ph{id:'PH8'}), (r:Road {id:'R9'})   MERGE (ph)-[:CONNECTED_BY]->(r);

// ============================================================
// APPROVISIONNEMENT (rift logistique)
// ============================================================
MATCH (h1x {id:'H1'}),  (w:Warehouse {id:'W1'}) MERGE (h1x)-[:SUPPLIED_BY {product:'médicaments', base_days:3}]->(w);
MATCH (h2x {id:'H2'}),  (w:Warehouse {id:'W2'}) MERGE (h2x)-[:SUPPLIED_BY {product:'médicaments', base_days:5}]->(w);
MATCH (h3x {id:'H3'}),  (w:Warehouse {id:'W3'}) MERGE (h3x)-[:SUPPLIED_BY {product:'médicaments', base_days:4}]->(w);
MATCH (h4x {id:'H4'}),  (w:Warehouse {id:'W1'}) MERGE (h4x)-[:SUPPLIED_BY {product:'médicaments', base_days:4}]->(w);
MATCH (h5x {id:'H5'}),  (w:Warehouse {id:'W1'}) MERGE (h5x)-[:SUPPLIED_BY {product:'médicaments', base_days:5}]->(w);
MATCH (ph1x {id:'PH1'}),(w:Warehouse {id:'W1'}) MERGE (ph1x)-[:SUPPLIED_BY {product:'médicaments'}]->(w);
MATCH (ph2x {id:'PH2'}),(w:Warehouse {id:'W1'}) MERGE (ph2x)-[:SUPPLIED_BY {product:'médicaments'}]->(w);
MATCH (ph3x {id:'PH3'}),(w:Warehouse {id:'W2'}) MERGE (ph3x)-[:SUPPLIED_BY {product:'médicaments'}]->(w);
MATCH (ph4x {id:'PH4'}),(w:Warehouse {id:'W2'}) MERGE (ph4x)-[:SUPPLIED_BY {product:'médicaments'}]->(w);
MATCH (ph5x {id:'PH5'}),(w:Warehouse {id:'W3'}) MERGE (ph5x)-[:SUPPLIED_BY {product:'médicaments'}]->(w);
MATCH (ph6x {id:'PH6'}),(w:Warehouse {id:'W1'}) MERGE (ph6x)-[:SUPPLIED_BY {product:'médicaments'}]->(w);
MATCH (ph7x {id:'PH7'}),(w:Warehouse {id:'W1'}) MERGE (ph7x)-[:SUPPLIED_BY {product:'médicaments'}]->(w);
MATCH (ph8x {id:'PH8'}),(w:Warehouse {id:'W1'}) MERGE (ph8x)-[:SUPPLIED_BY {product:'médicaments'}]->(w);

// ============================================================
// LOCALISATION GEOGRAPHIQUE
// ============================================================
UNWIND [
 ['P1','Z1'], ['P3','Z3'], ['P4','Z4'], ['P5','Z1'],
 ['T1','Z1'], ['T3','Z3'], ['T4','Z4'], ['T6','Z1'], ['T5','Z1'],
 ['T10','Z2'], ['T7','Z2'], ['T9','Z4'],
 ['H1','Z1'], ['H2','Z2'], ['H3','Z3'], ['H4','Z4'], ['H5','Z4'],
 ['W2','Z2'], ['W3','Z3'], ['W1','Z1'],
 ['PH1','Z1'], ['PH2','Z1'], ['PH3','Z2'], ['PH4','Z2'], ['PH5','Z3'],
 ['PH6','Z4'], ['PH7','Z4'], ['PH8','Z4']
] AS paire
MATCH (n:Infrastructure {id: paire[0]}), (z:Zone {id: paire[1]})
MERGE (n)-[:LOCATED_IN]->(z);

UNWIND [
 ['P2','Z2'], ['T2','Z2'], ['T8','Z4']
] AS paire
MATCH (n:Infrastructure {id: paire[0]}), (z:Zone {id: paire[1]})
MERGE (n)-[:LOCATED_IN]->(z);

UNWIND [
 ['R6','Z1'], ['R7','Z1'], ['R8','Z1'], ['R21','Z1'], ['R23','Z1'], ['R25','Z1'], ['R27','Z1'], ['R30','Z1'],
 ['R9','Z2'], ['R10','Z2'], ['R11','Z2'], ['R26','Z2'],
 ['R12','Z3'], ['R13','Z3'], ['R14','Z3'], ['R20','Z3'],
 ['R15','Z4'], ['R16','Z4'], ['R17','Z4'], ['R19','Z4'], ['R24','Z4'], ['R29','Z4'],
 ['R18','Z4'], ['R22','Z4'], ['R28','Z4']
] AS paire
MATCH (n:Road:Infrastructure {id: paire[0]}), (z:Zone {id: paire[1]})
MERGE (n)-[:LOCATED_IN]->(z);

// ============================================================
// ENRICHISSEMENT v3 - CASCADES MULTI-DOMAINES
// Données synthétiques pour les scénarios Vigie Urbaine.
// ============================================================

// ------------------------------------------------------------
// 1) PROPRIETES TELECOM : criticité + autonomie de secours
// ------------------------------------------------------------
MATCH (t:TelecomTower {id:'T1'})  SET t.criticality=5, t.backup_power_hours=1;
MATCH (t:TelecomTower {id:'T2'})  SET t.criticality=4, t.backup_power_hours=3;
MATCH (t:TelecomTower {id:'T3'})  SET t.criticality=5, t.backup_power_hours=2;
MATCH (t:TelecomTower {id:'T4'})  SET t.criticality=4, t.backup_power_hours=1;
MATCH (t:TelecomTower {id:'T5'})  SET t.criticality=4, t.backup_power_hours=4;
MATCH (t:TelecomTower {id:'T6'})  SET t.criticality=4, t.backup_power_hours=2;
MATCH (t:TelecomTower {id:'T7'})  SET t.criticality=5, t.backup_power_hours=3;
MATCH (t:TelecomTower {id:'T8'})  SET t.criticality=3, t.backup_power_hours=2;
MATCH (t:TelecomTower {id:'T9'})  SET t.criticality=4, t.backup_power_hours=1;
MATCH (t:TelecomTower {id:'T10'}) SET t.criticality=4, t.backup_power_hours=4;

// ------------------------------------------------------------
// 2) CRITICITE DES DEPOTS + STOCKS OPERATIONNELS
// ------------------------------------------------------------
MATCH (w:Warehouse {id:'W1'}) SET w.criticality=5, w.logistics_priority='CRITICAL';
MATCH (w:Warehouse {id:'W2'}) SET w.criticality=4, w.logistics_priority='HIGH';
MATCH (w:Warehouse {id:'W3'}) SET w.criticality=4, w.logistics_priority='HIGH';

// ------------------------------------------------------------
// 3) STOCKS SYNTHETIQUES DES PHARMACIES
// ------------------------------------------------------------
MATCH (p:Pharmacy {id:'PH1'}) SET p.medicine_stock_days=2;
MATCH (p:Pharmacy {id:'PH2'}) SET p.medicine_stock_days=3;
MATCH (p:Pharmacy {id:'PH3'}) SET p.medicine_stock_days=4;
MATCH (p:Pharmacy {id:'PH4'}) SET p.medicine_stock_days=2;
MATCH (p:Pharmacy {id:'PH5'}) SET p.medicine_stock_days=3;
MATCH (p:Pharmacy {id:'PH6'}) SET p.medicine_stock_days=2;
MATCH (p:Pharmacy {id:'PH7'}) SET p.medicine_stock_days=2;
MATCH (p:Pharmacy {id:'PH8'}) SET p.medicine_stock_days=3;

// ------------------------------------------------------------
// 4) DEPENDANCES TELECOM DES HOPITAUX
// Permet : CYBER_ATTACK/POWER_FAILURE -> antenne -> hôpital
// ------------------------------------------------------------
MATCH (h:Hospital {id:'H1'}), (t:TelecomTower {id:'T1'})
MERGE (h)-[:DEPENDS_ON {reason:'communications urgences', domain:'TELECOM', synthetic:true}]->(t);

MATCH (h:Hospital {id:'H2'}), (t:TelecomTower {id:'T7'})
MERGE (h)-[:DEPENDS_ON {reason:'communications urgences', domain:'TELECOM', synthetic:true}]->(t);

MATCH (h:Hospital {id:'H3'}), (t:TelecomTower {id:'T3'})
MERGE (h)-[:DEPENDS_ON {reason:'communications urgences', domain:'TELECOM', synthetic:true}]->(t);

MATCH (h:Hospital {id:'H4'}), (t:TelecomTower {id:'T4'})
MERGE (h)-[:DEPENDS_ON {reason:'communications urgences', domain:'TELECOM', synthetic:true}]->(t);

MATCH (h:Hospital {id:'H5'}), (t:TelecomTower {id:'T9'})
MERGE (h)-[:DEPENDS_ON {reason:'communications urgences', domain:'TELECOM', synthetic:true}]->(t);

// ------------------------------------------------------------
// 5) DEPENDANCES TELECOM DES PHARMACIES
// Rend les cyberattaques et pannes télécom plus visibles dans la cascade.
// ------------------------------------------------------------
MATCH (p:Pharmacy {id:'PH1'}), (t:TelecomTower {id:'T6'})
MERGE (p)-[:DEPENDS_ON {reason:'réseau paiement/stock', domain:'TELECOM', synthetic:true}]->(t);

MATCH (p:Pharmacy {id:'PH2'}), (t:TelecomTower {id:'T1'})
MERGE (p)-[:DEPENDS_ON {reason:'réseau paiement/stock', domain:'TELECOM', synthetic:true}]->(t);

MATCH (p:Pharmacy {id:'PH3'}), (t:TelecomTower {id:'T7'})
MERGE (p)-[:DEPENDS_ON {reason:'réseau paiement/stock', domain:'TELECOM', synthetic:true}]->(t);

MATCH (p:Pharmacy {id:'PH4'}), (t:TelecomTower {id:'T7'})
MERGE (p)-[:DEPENDS_ON {reason:'réseau paiement/stock', domain:'TELECOM', synthetic:true}]->(t);

MATCH (p:Pharmacy {id:'PH5'}), (t:TelecomTower {id:'T3'})
MERGE (p)-[:DEPENDS_ON {reason:'réseau paiement/stock', domain:'TELECOM', synthetic:true}]->(t);

MATCH (p:Pharmacy {id:'PH6'}), (t:TelecomTower {id:'T4'})
MERGE (p)-[:DEPENDS_ON {reason:'réseau paiement/stock', domain:'TELECOM', synthetic:true}]->(t);

MATCH (p:Pharmacy {id:'PH7'}), (t:TelecomTower {id:'T9'})
MERGE (p)-[:DEPENDS_ON {reason:'réseau paiement/stock', domain:'TELECOM', synthetic:true}]->(t);

MATCH (p:Pharmacy {id:'PH8'}), (t:TelecomTower {id:'T9'})
MERGE (p)-[:DEPENDS_ON {reason:'réseau paiement/stock', domain:'TELECOM', synthetic:true}]->(t);

// ------------------------------------------------------------
// 6) DEPENDANCES TELECOM DES DEPOTS
// ------------------------------------------------------------
MATCH (w:Warehouse {id:'W1'}), (t:TelecomTower {id:'T6'})
MERGE (w)-[:DEPENDS_ON {reason:'WMS / communications logistiques', domain:'TELECOM', synthetic:true}]->(t);

MATCH (w:Warehouse {id:'W2'}), (t:TelecomTower {id:'T7'})
MERGE (w)-[:DEPENDS_ON {reason:'WMS / communications logistiques', domain:'TELECOM', synthetic:true}]->(t);

MATCH (w:Warehouse {id:'W3'}), (t:TelecomTower {id:'T3'})
MERGE (w)-[:DEPENDS_ON {reason:'WMS / communications logistiques', domain:'TELECOM', synthetic:true}]->(t);

// ------------------------------------------------------------
// 7) DEPENDANCES ELECTRIQUES DES DEPOTS
// ------------------------------------------------------------
MATCH (w:Warehouse {id:'W1'}), (p:PowerStation {id:'P1'})
MERGE (w)-[:DEPENDS_ON {reason:'chaîne du froid / alimentation', domain:'POWER', synthetic:true}]->(p);

MATCH (w:Warehouse {id:'W2'}), (p:PowerStation {id:'P2'})
MERGE (w)-[:DEPENDS_ON {reason:'chaîne du froid / alimentation', domain:'POWER', synthetic:true}]->(p);

MATCH (w:Warehouse {id:'W3'}), (p:PowerStation {id:'P3'})
MERGE (w)-[:DEPENDS_ON {reason:'chaîne du froid / alimentation', domain:'POWER', synthetic:true}]->(p);

// ------------------------------------------------------------
// 8) ENRICHISSEMENT DES ROUTES
// Ces propriétés sont préparées pour une prochaine version du Risk Engine.
// ------------------------------------------------------------
MATCH (r:Road {id:'R1'})  SET r.criticality=5, r.traffic_importance=5, r.flood_susceptibility=2;
MATCH (r:Road {id:'R2'})  SET r.criticality=5, r.traffic_importance=5, r.flood_susceptibility=3;
MATCH (r:Road {id:'R3'})  SET r.criticality=4, r.traffic_importance=4, r.flood_susceptibility=4;
MATCH (r:Road {id:'R4'})  SET r.criticality=4, r.traffic_importance=4, r.flood_susceptibility=2;
MATCH (r:Road {id:'R5'})  SET r.criticality=5, r.traffic_importance=5, r.flood_susceptibility=4;

UNWIND [
 'R6','R7','R8','R9','R10','R11','R12','R13','R14','R15',
 'R16','R17','R18','R19','R20','R21','R22','R23','R24','R25',
 'R26','R27','R28','R29','R30'
] AS rid
MATCH (r:Road {id:rid})
SET
  r.criticality = coalesce(r.criticality, 2),
  r.traffic_importance = coalesce(r.traffic_importance, 2),
  r.flood_susceptibility = coalesce(r.flood_susceptibility, 3);

// Quelques axes plus sensibles pour les scénarios météo.
MATCH (r:Road {id:'R7'})  SET r.flood_susceptibility=4;
MATCH (r:Road {id:'R8'})  SET r.flood_susceptibility=5;
MATCH (r:Road {id:'R12'}) SET r.flood_susceptibility=4;
MATCH (r:Road {id:'R16'}) SET r.flood_susceptibility=5;
MATCH (r:Road {id:'R17'}) SET r.flood_susceptibility=4;
MATCH (r:Road {id:'R19'}) SET r.flood_susceptibility=5;

// ------------------------------------------------------------
// 9) MARQUAGE DES RELATIONS DE SIMULATION
// On garde une trace explicite qu'il s'agit d'un modèle académique.
// ------------------------------------------------------------
MATCH ()-[rel:DEPENDS_ON]->()
SET rel.model='Vigie Urbaine', rel.simulation=true;

MATCH ()-[rel:SUPPLIED_BY]->()
SET rel.model='Vigie Urbaine', rel.simulation=true;

MATCH ()-[rel:CONNECTED_BY]->()
SET rel.model='Vigie Urbaine', rel.simulation=true;

// ============================================================
// REQUETES DE CONTROLE (à lancer séparément si besoin)
// ============================================================
// 1. Vérifier les cascades électriques / télécom :
// MATCH p=(x:Infrastructure)-[:DEPENDS_ON*1..5]->(pwr:PowerStation {id:'P1'})
// RETURN p;
//
// 2. Vérifier un scénario cyber sur T1 :
// MATCH p=(x:Infrastructure)-[:DEPENDS_ON*1..5]->(t:TelecomTower {id:'T1'})
// RETURN p;
//
// 3. Vérifier l'approvisionnement depuis W1 :
// MATCH (s:Infrastructure)-[:SUPPLIED_BY]->(w:Warehouse {id:'W1'})
// RETURN s,w;
//
// 4. Vérifier les infrastructures de Tunis Centre :
// MATCH (i:Infrastructure)-[:LOCATED_IN]->(z:Zone {id:'Z1'})
// RETURN i,z;
//
// 5. Vérifier les routes sensibles aux inondations :
// MATCH (r:Road)
// WHERE r.flood_susceptibility >= 4
// RETURN r.id, r.name, r.flood_susceptibility
// ORDER BY r.flood_susceptibility DESC;

// ============================================================
// GEOMETRIE DES ROUTES (v4) - TRACES GPS SYNTHETIQUES
// Chaque route = trace de points [lat1, lon1, lat2, lon2, ...]
// alignee sur la vraie geographie du Grand Tunis (rue -> parcours).
// Sert au rendu polyline sur la carte (MapView).
// ============================================================

// --- Arteres R1-R5 : traversent plusieurs zones ---
MATCH (r:Road {id:'R1'}) SET r.path=[36.750,10.245, 36.790,10.255, 36.835,10.262, 36.875,10.275];
MATCH (r:Road {id:'R2'}) SET r.path=[36.799,10.190, 36.806,10.186, 36.811,10.184];
MATCH (r:Road {id:'R3'}) SET r.path=[36.818,10.188, 36.830,10.176, 36.842,10.170];
MATCH (r:Road {id:'R4'}) SET r.path=[36.813,10.193, 36.838,10.190, 36.862,10.196, 36.878,10.210];
MATCH (r:Road {id:'R5'}) SET r.path=[36.782,10.190, 36.797,10.222, 36.812,10.248, 36.828,10.262];

// --- Z1 Tunis Centre ---
MATCH (r:Road {id:'R6'})  SET r.path=[36.800,10.184, 36.806,10.182];
MATCH (r:Road {id:'R7'})  SET r.path=[36.809,10.196, 36.816,10.192];
MATCH (r:Road {id:'R8'})  SET r.path=[36.812,10.200, 36.818,10.190];
MATCH (r:Road {id:'R21'}) SET r.path=[36.809,10.177, 36.800,10.175];
MATCH (r:Road {id:'R23'}) SET r.path=[36.798,10.175, 36.795,10.180];
MATCH (r:Road {id:'R25'}) SET r.path=[36.812,10.168, 36.817,10.172];
MATCH (r:Road {id:'R27'}) SET r.path=[36.818,10.180, 36.823,10.186];
MATCH (r:Road {id:'R30'}) SET r.path=[36.812,10.176, 36.818,10.180];

// --- Z2 La Marsa / Gammarth ---
MATCH (r:Road {id:'R9'})  SET r.path=[36.880,10.298, 36.878,10.288];
MATCH (r:Road {id:'R10'}) SET r.path=[36.876,10.305, 36.880,10.310];
MATCH (r:Road {id:'R11'}) SET r.path=[36.868,10.293, 36.866,10.299];
MATCH (r:Road {id:'R26'}) SET r.path=[36.881,10.322, 36.884,10.317, 36.886,10.312];

// --- Z3 L'Ariana ---
MATCH (r:Road {id:'R12'}) SET r.path=[36.852,10.205, 36.856,10.198];
MATCH (r:Road {id:'R13'}) SET r.path=[36.851,10.216, 36.854,10.210];
MATCH (r:Road {id:'R14'}) SET r.path=[36.855,10.240, 36.850,10.248];
MATCH (r:Road {id:'R20'}) SET r.path=[36.859,10.242, 36.862,10.249];

// --- Z4 Ben Arous / Sud ---
MATCH (r:Road {id:'R15'}) SET r.path=[36.791,10.216, 36.794,10.221];
MATCH (r:Road {id:'R16'}) SET r.path=[36.787,10.211, 36.783,10.206];
MATCH (r:Road {id:'R17'}) SET r.path=[36.746,10.213, 36.741,10.220];
MATCH (r:Road {id:'R18'}) SET r.path=[36.796,10.233, 36.800,10.238];
MATCH (r:Road {id:'R19'}) SET r.path=[36.785,10.222, 36.780,10.228, 36.776,10.234];
MATCH (r:Road {id:'R22'}) SET r.path=[36.823,10.245, 36.818,10.252];
MATCH (r:Road {id:'R24'}) SET r.path=[36.752,10.228, 36.754,10.233];
MATCH (r:Road {id:'R28'}) SET r.path=[36.806,10.246, 36.802,10.251];
MATCH (r:Road {id:'R29'}) SET r.path=[36.750,10.218, 36.748,10.224];

// ============================================================
// RESEAU ROUTIER v5 - RELATIONS CONNECTS_TO (routage)
// Artere-artere + quartier-quartier, construites sur la vraie
// geometrie des traces GPS. Dernier sommet/exposition:
// flood_susceptibility = celle de la route ARRIvEE (exposee).
// Le statut n'est PAS stocke sur l'arete (il change avec les
// incidents) : le moteur de routage lit Road.status en direct.
// ============================================================

UNWIND [
 ['R1','R4', 2.5, 4, 1], ['R1','R9', 3.0, 5, 2], ['R2','R3', 1.4, 3, 2],
 ['R4','R12', 1.8, 3, 2], ['R4','R13', 1.5, 3, 2], ['R4','R20', 2.2, 4, 2],
 ['R3','R8', 1.2, 3, 2], ['R3','R7', 1.6, 3, 2], ['R3','R27', 1.9, 4, 2],
 ['R5','R18', 2.0, 4, 2], ['R5','R28', 1.6, 3, 2], ['R5','R22', 1.4, 3, 2],
 ['R5','R19', 2.6, 5, 2],
 ['R2','R6', 0.7, 2, 3], ['R2','R7', 1.0, 2, 3], ['R2','R21', 1.2, 3, 2],
 ['R2','R23', 1.0, 2, 3], ['R2','R8', 1.8, 4, 2], ['R2','R16', 1.6, 4, 3],
 ['R6','R23', 0.6, 2, 3], ['R6','R21', 0.8, 2, 3], ['R6','R7', 1.1, 3, 2],
 ['R7','R8', 0.9, 2, 2], ['R25','R30', 1.2, 3, 2], ['R27','R30', 0.8, 2, 2],
 ['R21','R25', 0.7, 2, 2], ['R30','R8', 1.1, 2, 2], ['R27','R8', 1.0, 2, 2],
 ['R9','R10', 1.5, 3, 2], ['R9','R11', 1.2, 3, 2], ['R10','R26', 1.3, 3, 2],
 ['R12','R13', 1.2, 3, 2], ['R13','R14', 2.8, 5, 2], ['R14','R20', 1.2, 3, 2],
 ['R15','R16', 1.3, 3, 2], ['R16','R19', 1.1, 3, 3], ['R15','R18', 1.4, 3, 2],
 ['R17','R29', 0.9, 2, 2], ['R29','R24', 1.6, 3, 2], ['R22','R28', 1.9, 4, 2]
] AS segment
MATCH (a:Road {id: segment[0]}), (b:Road {id: segment[1]})
MERGE (a)-[e1:CONNECTS_TO]->(b)
MERGE (b)-[e2:CONNECTS_TO]->(a)
SET e1.distance_km = segment[2], e1.travel_time_min = segment[3],
    e1.traffic_level = segment[4],
    e1.flood_susceptibility = coalesce(b.flood_susceptibility, 2),
    e2.distance_km = segment[2], e2.travel_time_min = segment[3],
    e2.traffic_level = segment[4],
    e2.flood_susceptibility = coalesce(a.flood_susceptibility, 2);

// --- v5.1 : ECHANGEURS INTER-COMPQSANTES (connectivite reseau) ---
UNWIND [
 ['R3','R4', 2.2, 4, 2], ['R1','R5', 3.4, 5, 1], ['R22','R14', 2.0, 4, 2],
 ['R5','R2', 2.8, 4, 2], ['R4','R1', 2.0, 4, 1], ['R3','R5', 3.8, 6, 2]
] AS segment
MATCH (a:Road {id: segment[0]}), (b:Road {id: segment[1]})
MERGE (a)-[e1:CONNECTS_TO]->(b)
MERGE (b)-[e2:CONNECTS_TO]->(a)
SET e1.distance_km = segment[2], e1.travel_time_min = segment[3],
    e1.traffic_level = segment[4],
    e1.flood_susceptibility = coalesce(b.flood_susceptibility, 2),
    e2.distance_km = segment[2], e2.travel_time_min = segment[3],
    e2.traffic_level = segment[4],
    e2.flood_susceptibility = coalesce(a.flood_susceptibility, 2);

// --- v5.2 : AJUSTEMENT BEN AROUS (exits R24/R29/R17) ---
UNWIND [
 ['R24','R5', 3.0, 6, 2], ['R29','R5', 2.8, 5, 2]
] AS segment
MATCH (a:Road {id: segment[0]}), (b:Road {id: segment[1]})
MERGE (a)-[e1:CONNECTS_TO]->(b)
MERGE (b)-[e2:CONNECTS_TO]->(a)
SET e1.distance_km = segment[2], e1.travel_time_min = segment[3],
    e1.traffic_level = segment[4],
    e1.flood_susceptibility = coalesce(b.flood_susceptibility, 2),
    e2.distance_km = segment[2], e2.travel_time_min = segment[3],
    e2.traffic_level = segment[4],
    e2.flood_susceptibility = coalesce(a.flood_susceptibility, 2);

// ===== v6 - CHEMINS GPS REELS OpenStreetMap / Nominatim (idempotent) =====
MATCH (r:Road:Infrastructure {id:'R2'}) SET r.path = [36.85621, 10.18795, 36.85581, 10.18782, 36.85569, 10.18777, 36.85558, 10.18769, 36.85546, 10.1876, 36.85532, 10.18744, 36.85515, 10.1872, 36.855, 10.18698, 36.85497, 10.18694, 36.85489, 10.18684, 36.85475, 10.1867, 36.85467, 10.18662, 36.85442, 10.1864, 36.85421, 10.18624, 36.85382, 10.18597, 36.85367, 10.18585, 36.85356, 10.18575, 36.85341, 10.18559, 36.8533, 10.18547, 36.85318, 10.18533, 36.85314, 10.18528, 36.85297, 10.18513, 36.85274, 10.18492, 36.85197, 10.18419, 36.85151, 10.18376, 36.8511, 10.18339, 36.851, 10.1833, 36.85096, 10.18325, 36.85079, 10.18313, 36.85063, 10.18303, 36.85041, 10.18294, 36.85023, 10.18288, 36.85008, 10.18285, 36.84996, 10.18283, 36.84977, 10.18281, 36.84965, 10.18281, 36.84937, 10.18281, 36.84912, 10.18284, 36.84908, 10.18285, 36.84903, 10.18287, 36.84883, 10.18295, 36.84878, 10.18298, 36.84872, 10.183, 36.84844, 10.18312, 36.84827, 10.18319, 36.84815, 10.18322];
MATCH (r:Road:Infrastructure {id:'R5'}) SET r.path = [36.77411, 10.22885, 36.77426, 10.22861, 36.77467, 10.22798, 36.77507, 10.22732, 36.77567, 10.22639, 36.7757, 10.22634, 36.77593, 10.22597, 36.77625, 10.22546, 36.77684, 10.22449, 36.77711, 10.22403];
MATCH (r:Road:Infrastructure {id:'R6'}) SET r.path = [36.80622, 10.18141, 36.80585, 10.18148, 36.80578, 10.18149, 36.80503, 10.18159, 36.8045, 10.18166, 36.80377, 10.18178, 36.80291, 10.18192, 36.80231, 10.18203, 36.80181, 10.1821, 36.8016, 10.18214, 36.80156, 10.18214, 36.80129, 10.18219];
MATCH (r:Road:Infrastructure {id:'R7'}) SET r.path = [36.80916, 10.14881, 36.8091, 10.14882, 36.80904, 10.14883, 36.80703, 10.14955, 36.80693, 10.14957, 36.80645, 10.14973, 36.80595, 10.1499, 36.80569, 10.15, 36.80531, 10.15011, 36.80513, 10.15018, 36.80489, 10.15026, 36.80449, 10.15039, 36.80367, 10.1507, 36.80328, 10.15084, 36.80319, 10.15088, 36.80281, 10.15101, 36.80245, 10.15116, 36.80181, 10.15139, 36.80161, 10.15146, 36.8015, 10.15151];
MATCH (r:Road:Infrastructure {id:'R8'}) SET r.path = [36.80593, 10.16603, 36.80595, 10.166, 36.80603, 10.16584, 36.80609, 10.16569, 36.80627, 10.16528, 36.80631, 10.16521, 36.80647, 10.16488, 36.80653, 10.16471, 36.80659, 10.16454, 36.80664, 10.16439, 36.80672, 10.16408, 36.80677, 10.1639, 36.80683, 10.1637, 36.80684, 10.16366, 36.80691, 10.1634, 36.80708, 10.16285, 36.80733, 10.16197, 36.80738, 10.16185, 36.80742, 10.16174, 36.80774, 10.16124, 36.80804, 10.16053, 36.80812, 10.1603, 36.80829, 10.15992];
MATCH (r:Road:Infrastructure {id:'R9'}) SET r.path = [36.89876, 10.2925, 36.89836, 10.29276, 36.89787, 10.29307, 36.89715, 10.29357, 36.89648, 10.29402, 36.89646, 10.29404, 36.89606, 10.29432, 36.89571, 10.29455, 36.89458, 10.29534, 36.89409, 10.29568, 36.8933, 10.29621, 36.89313, 10.29633, 36.8928, 10.29656, 36.89246, 10.29679, 36.89124, 10.29763, 36.88969, 10.29868, 36.88888, 10.29925, 36.88863, 10.29942, 36.8881, 10.29979, 36.88776, 10.30002, 36.88744, 10.30026, 36.88705, 10.30052];
MATCH (r:Road:Infrastructure {id:'R10'}) SET r.path = [36.8644, 10.3156, 36.8644, 10.31551, 36.8644, 10.31543, 36.86439, 10.31536, 36.86436, 10.31522, 36.86431, 10.31507, 36.86409, 10.3145, 36.86399, 10.31423, 36.86397, 10.31414, 36.86396, 10.31405, 36.86397, 10.31392, 36.86398, 10.3136, 36.86397, 10.31324, 36.86397, 10.31313, 36.86397, 10.31283, 36.86398, 10.31257, 36.86399, 10.31232, 36.86416, 10.31153, 36.86439, 10.31049, 36.86449, 10.31009, 36.86453, 10.30984, 36.86456, 10.30969, 36.86459, 10.30951, 36.86466, 10.30918, 36.86476, 10.30873, 36.86482, 10.3085, 36.86482, 10.30835, 36.8648, 10.30821, 36.86476, 10.30795, 36.86471, 10.30781, 36.86467, 10.30772, 36.86462, 10.30761, 36.86456, 10.3075, 36.8645, 10.30738, 36.86443, 10.30715, 36.86438, 10.30693, 36.86434, 10.30676, 36.86431, 10.30649, 36.86427, 10.30627, 36.86419, 10.30595, 36.86413, 10.30572, 36.86406, 10.30545];
MATCH (r:Road:Infrastructure {id:'R11'}) SET r.path = [36.86674, 10.30985, 36.8667, 10.30962, 36.86665, 10.30925, 36.86662, 10.30915, 36.8666, 10.30911, 36.86657, 10.30909, 36.86652, 10.30908, 36.86646, 10.30909, 36.86577, 10.30935, 36.86493, 10.30968, 36.86466, 10.30979, 36.86453, 10.30984, 36.86425, 10.30999, 36.86396, 10.31016, 36.8636, 10.31036, 36.86329, 10.31055, 36.86284, 10.31083];
MATCH (r:Road:Infrastructure {id:'R12'}) SET r.path = [36.83015, 10.11456, 36.83051, 10.11448, 36.83086, 10.11437, 36.83092, 10.11435, 36.83103, 10.11431, 36.83151, 10.11413, 36.83205, 10.11395, 36.83252, 10.11376, 36.83281, 10.11364, 36.8333, 10.11346, 36.83369, 10.1133, 36.83392, 10.11322, 36.83412, 10.11315, 36.83433, 10.11306, 36.83462, 10.1129, 36.83482, 10.11277, 36.83501, 10.11263, 36.83511, 10.11258, 36.83529, 10.11247, 36.83559, 10.11228, 36.83576, 10.11221, 36.83594, 10.11215, 36.83602, 10.11212, 36.83607, 10.11212, 36.83613, 10.11212, 36.83653, 10.11211, 36.83666, 10.11209, 36.8367, 10.11209, 36.83692, 10.11203, 36.83716, 10.11195, 36.8372, 10.11194, 36.83742, 10.11191, 36.83765, 10.11189, 36.83776, 10.11189, 36.83808, 10.11183, 36.83812, 10.11182];
MATCH (r:Road:Infrastructure {id:'R13'}) SET r.path = [36.79072, 10.18382, 36.79126, 10.18373, 36.79216, 10.18358, 36.79259, 10.18351, 36.79358, 10.18335, 36.79436, 10.18323, 36.79472, 10.18318, 36.79513, 10.18312, 36.79573, 10.18303, 36.79638, 10.18291, 36.7966, 10.18287];
MATCH (r:Road:Infrastructure {id:'R15'}) SET r.path = [36.80257, 10.18482, 36.80262, 10.18481, 36.80274, 10.1848, 36.80318, 10.18473, 36.8034, 10.1847, 36.80399, 10.1846, 36.80433, 10.18456, 36.80434, 10.18456, 36.80435, 10.18456, 36.80481, 10.1845, 36.80528, 10.18443, 36.80545, 10.18441, 36.80609, 10.18431, 36.80652, 10.18423, 36.80738, 10.1841, 36.80773, 10.18405, 36.80834, 10.18397, 36.80859, 10.18393];
MATCH (r:Road:Infrastructure {id:'R18'}) SET r.path = [36.77098, 10.23552, 36.77097, 10.23563, 36.77095, 10.23582, 36.77092, 10.23594, 36.77086, 10.23608, 36.77076, 10.23623, 36.77062, 10.23637, 36.77015, 10.23688, 36.76968, 10.23737, 36.76939, 10.23765, 36.76913, 10.23793];
MATCH (r:Road:Infrastructure {id:'R22'}) SET r.path = [36.84091, 10.24779, 36.84081, 10.24767, 36.84073, 10.2476, 36.84058, 10.24749, 36.84042, 10.24739, 36.84022, 10.24724, 36.84014, 10.24719, 36.84, 10.24711, 36.83957, 10.24687, 36.83891, 10.24649, 36.83878, 10.24642, 36.83812, 10.24604, 36.83764, 10.24577, 36.83752, 10.24567, 36.83742, 10.24557, 36.83732, 10.24544, 36.83722, 10.2453, 36.83712, 10.24513, 36.83702, 10.24494, 36.83693, 10.24475, 36.83685, 10.24453, 36.83661, 10.24371, 36.83642, 10.24304, 36.83625, 10.24246, 36.83611, 10.24198, 36.83608, 10.24184, 36.83604, 10.24172, 36.8359, 10.24123, 36.83576, 10.24072, 36.83572, 10.2406];
MATCH (r:Road:Infrastructure {id:'R23'}) SET r.path = [36.74291, 10.21656, 36.74295, 10.21682, 36.74311, 10.2179, 36.74322, 10.21851, 36.74331, 10.21902, 36.74332, 10.21905, 36.74345, 10.21974, 36.74351, 10.22013, 36.74359, 10.22062, 36.7436, 10.22068, 36.74368, 10.22122, 36.74375, 10.22182, 36.74385, 10.22254, 36.74386, 10.22263, 36.74395, 10.22325, 36.74399, 10.2235, 36.74403, 10.22375, 36.7441, 10.22425, 36.74417, 10.22465, 36.74426, 10.2253, 36.74439, 10.22607];
MATCH (r:Road:Infrastructure {id:'R24'}) SET r.path = [36.70718, 10.18533, 36.70737, 10.1846, 36.70752, 10.18401, 36.70766, 10.18356, 36.7083, 10.18128];
MATCH (r:Road:Infrastructure {id:'R25'}) SET r.path = [36.81344, 10.18409, 36.81271, 10.1842, 36.81173, 10.18438, 36.81168, 10.18438, 36.81143, 10.18443, 36.8113, 10.18445, 36.81088, 10.18452, 36.81048, 10.18459, 36.80884, 10.18486, 36.80867, 10.18488, 36.80679, 10.1852, 36.80676, 10.1852, 36.80663, 10.18522, 36.80653, 10.18524, 36.80509, 10.18547, 36.80459, 10.18555, 36.80429, 10.1856, 36.80395, 10.18566, 36.80333, 10.18577, 36.80298, 10.18583, 36.80266, 10.18587, 36.80166, 10.18604, 36.80111, 10.18613, 36.80102, 10.18614, 36.80092, 10.18617];
MATCH (r:Road:Infrastructure {id:'R26'}) SET r.path = [36.92159, 10.30713, 36.92163, 10.30709, 36.9217, 10.30701, 36.92175, 10.30696, 36.92179, 10.3069, 36.92181, 10.30685, 36.9218, 10.3068, 36.92178, 10.30674, 36.92173, 10.30667, 36.92167, 10.3066, 36.92161, 10.30654, 36.92149, 10.30644, 36.92136, 10.30636, 36.92119, 10.30627, 36.92103, 10.30621, 36.92088, 10.30617, 36.92077, 10.30611, 36.92072, 10.30606, 36.92068, 10.306, 36.9206, 10.30588, 36.92057, 10.30582, 36.92053, 10.30574, 36.92048, 10.30565, 36.92041, 10.30557, 36.92033, 10.3055, 36.92024, 10.30544, 36.92018, 10.30542, 36.92011, 10.30541, 36.92004, 10.30541, 36.91996, 10.30541, 36.91992, 10.30541, 36.91987, 10.30542, 36.91982, 10.30544, 36.91977, 10.30547];
MATCH (r:Road:Infrastructure {id:'R27'}) SET r.path = [36.8343, 10.23713, 36.83404, 10.23725, 36.83357, 10.23747, 36.83307, 10.23769, 36.83273, 10.23784, 36.83267, 10.23787, 36.83261, 10.23787, 36.83258, 10.23784, 36.83254, 10.23778, 36.8324, 10.23731, 36.83225, 10.23684, 36.83225, 10.23676, 36.83228, 10.23668, 36.83234, 10.23663, 36.83272, 10.23645, 36.83321, 10.23624, 36.83369, 10.23602, 36.83375, 10.23599, 36.83381, 10.23596, 36.83395, 10.2359];
MATCH (r:Road:Infrastructure {id:'R29'}) SET r.path = [36.77656, 10.21523, 36.77631, 10.216, 36.77582, 10.21768, 36.77573, 10.21796];
// autoroutes A1/A4 via Overpass (tag ref, idempotent)
MATCH (r:Road:Infrastructure {id:'R1'}) SET r.path = [36.78445, 10.19488, 36.78733, 10.19237, 36.79145, 10.19103, 36.78445, 10.19488, 36.78272, 10.19671, 36.78099, 10.19709, 36.77746, 10.197, 36.77569, 10.19736, 36.77525, 10.19744, 36.77429, 10.19776, 36.77308, 10.19772, 36.77146, 10.19718, 36.76914, 10.19615, 36.76752, 10.19581, 36.76603, 10.19586, 36.76434, 10.19639, 36.76195, 10.19787, 36.75746, 10.20058, 36.75513, 10.20196, 36.7431, 10.21283, 36.73809, 10.21785, 36.73359, 10.22532, 36.73184, 10.23013, 36.72943, 10.23793, 36.72803, 10.24629, 36.7269, 10.25052, 36.7243, 10.2571, 36.71847, 10.26644, 36.71575, 10.2718, 36.71379, 10.27784, 36.71268, 10.28102, 36.71096, 10.28427, 36.70774, 10.28831, 36.70349, 10.29444, 36.69868, 10.30141, 36.695, 10.30542, 36.69244, 10.30864, 36.69019, 10.31176, 36.68882, 10.31354, 36.68779, 10.31477, 36.68672, 10.31597, 36.68545, 10.3173, 36.68403, 10.31872, 36.68227, 10.32038, 36.68032, 10.32227, 36.67712, 10.32489, 36.67307, 10.33065, 36.66927, 10.33592, 36.66656, 10.33937, 36.66329, 10.34257, 36.65334, 10.35079, 36.65058, 10.35372, 36.64711, 10.36061, 36.64589, 10.36485, 36.64576, 10.36573];
MATCH (r:Road:Infrastructure {id:'R4'}) SET r.path = [36.94863, 10.07834, 36.9502, 10.07645, 36.95503, 10.0706, 36.9578, 10.06727, 36.9602, 10.06445, 36.96134, 10.06316, 36.96325, 10.0611, 36.96516, 10.05917, 36.96718, 10.05723, 36.97181, 10.05303, 36.97467, 10.05047, 36.97574, 10.0495, 36.97849, 10.047, 36.9814, 10.04431, 36.98274, 10.0429, 36.98365, 10.04184, 36.98448, 10.04081, 36.98551, 10.03943, 36.98648, 10.03802, 36.98727, 10.0368, 36.94839, 10.0786, 36.9472, 10.08005, 36.94549, 10.08217, 36.94476, 10.08314, 36.94403, 10.0842, 36.94302, 10.08578, 36.94096, 10.08903, 36.94053, 10.08973, 36.93985, 10.09079, 36.939, 10.09197, 36.93814, 10.09298, 36.93723, 10.09392, 36.93628, 10.09475, 36.93582, 10.09511, 36.93541, 10.09542, 36.93482, 10.09585, 36.93447, 10.0961, 36.9342, 10.09629, 36.93388, 10.09652, 36.93352, 10.09677, 36.93305, 10.09711, 36.9327, 10.09736, 36.93207, 10.09781, 36.92946, 10.09965, 36.92628, 10.10192, 36.92572, 10.10225, 36.92558, 10.10235, 36.92532, 10.10253, 36.92507, 10.10277, 36.92474, 10.10299, 36.9239, 10.10356, 36.9219, 10.10498, 36.91948, 10.10672];
