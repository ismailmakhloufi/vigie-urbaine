// ============================================================
// URBAN BUTTERFLY - Graphe v2 : ville MVP complete (section 19)
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
// Données synthétiques pour les scénarios Urban Butterfly.
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
SET rel.model='Urban Butterfly', rel.simulation=true;

MATCH ()-[rel:SUPPLIED_BY]->()
SET rel.model='Urban Butterfly', rel.simulation=true;

MATCH ()-[rel:CONNECTED_BY]->()
SET rel.model='Urban Butterfly', rel.simulation=true;

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
