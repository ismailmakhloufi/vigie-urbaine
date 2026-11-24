import { NATURES_FR } from "./libelles.js";

const ALIASES = {
  Hospital: "hopital hopitaux clinique urgence",
  PowerStation: "poste electrique postes electriques centrale energie",
  TelecomTower: "antenne antennes telecom relais",
  Road: "rue rues route routes avenue boulevard voie voirie",
};

export function normalizeSearch(value) {
  return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("fr").replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

export function searchInfrastructure(infrastructure, input) {
  const query = normalizeSearch(input);
  if (!query) return [];
  return infrastructure.map((node) => {
    const name = normalizeSearch(node.name);
    const id = normalizeSearch(node.id);
    const kind = normalizeSearch(`${NATURES_FR[node.kind] || node.kind} ${ALIASES[node.kind] || ""}`);
    const names = [name, id];
    let rank = 4;
    if (names.some((text) => text.startsWith(query))) rank = 0;
    else if (names.some((text) => text.split(" ").some((word) => word.startsWith(query)))) rank = 1;
    else if (query.length >= 2 && kind.split(" ").some((word) => word.startsWith(query))) rank = 2;
    else if (query.length >= 3 && [...names, kind].some((text) => text.includes(query))) rank = 3;
    return { node, rank };
  }).filter(({ node, rank }) => rank < 4 && node.lat != null && node.lon != null)
    .sort((a, b) => a.rank - b.rank || a.node.name.localeCompare(b.node.name, "fr"))
    .map(({ node }) => node);
}
