// ============================================================
// URBAN BUTTERFLY - Graphe v2 : ville MVP complete (section 19)
// 4 zones <- 5 postes - 10 antennes - 5 hopitaux - 30 routes
//               - 8 pharmacies - 3 depots
// Idempotent : rejouer ne duplique rien (MERGE + IF NOT EXISTS)
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
