// Libellés français partagés entre les composants
export const NATURES_FR = {
  Hospital: "Hôpital",
  PowerStation: "Centrale électrique",
  TelecomTower: "Antenne télécom",
  Warehouse: "Dépôt logistique",
  Pharmacy: "Pharmacie",
  Road: "Route",
  Zone: "Zone météo",
};

export const PROFILS_FR = {
  NORMAL: "Patrouille",
  AMBULANCE: "Ambulance",
  SUPPLY: "Ravitaillement",
};

export const NIVEAUX_FR = {
  LOW: "FAIBLE",
  MEDIUM: "MOYEN",
  HIGH: "ÉLEVÉ",
  CRITICAL: "CRITIQUE",
};

export const ETYPES_FR = {
  HEAVY_RAIN: "Pluie extrême",
  ROAD_BLOCKED: "Route bloquée",
  POWER_FAILURE: "Panne électrique",
  CYBER_ATTACK: "Cyberattaque",
};

export const ETATS_VILLE_FR = {
  STABLE: "STABLE",
  WATCH: "VEILLE",
  DEGRADED: "DÉGRADÉ",
  CRITICAL: "CRITIQUE",
};

export const STATUTS_FR = {
  ONLINE: "Opérationnel",
  OPERATIONAL: "Opérationnel",
  CLEAR: "Dégagée",
  OFFLINE: "Hors service",
  COMPROMISED: "Compromis",
  BLOCKED: "Bloquée",
  UNKNOWN: "Inconnu",
};

export const NIVEAU = (r) =>
  NIVEAUX_FR[(r || "").toUpperCase()] || (r || "FAIBLE").toUpperCase();
