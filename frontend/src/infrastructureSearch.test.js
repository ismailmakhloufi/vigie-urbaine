import test from "node:test";
import assert from "node:assert/strict";
import { searchInfrastructure } from "./infrastructureSearch.js";

const nodes = [
  { id: "P1", name: "Station Nord", kind: "PowerStation", lat: 36.8, lon: 10.2 },
  { id: "T1", name: "Antenne Marsa", kind: "TelecomTower", lat: 36.9, lon: 10.3 },
  { id: "R1", name: "Rue de la République", kind: "Road", lat: 36.7, lon: 10.1 },
  { id: "H1", name: "Hôpital République", kind: "Hospital", lat: 36.75, lon: 10.15 },
  { id: "X1", name: "Rue invisible", kind: "Road", lat: null, lon: null },
];

test("une lettre propose les noms commençant par elle, puis les correspondances secondaires", () => {
  assert.deepEqual(searchInfrastructure(nodes, "R").map((node) => node.id), ["R1", "H1"]);
  assert.deepEqual(searchInfrastructure(nodes, "T").map((node) => node.id), ["T1"]);
});

test("recherche insensible aux accents, par identifiant et par synonyme de catégorie", () => {
  assert.deepEqual(searchInfrastructure(nodes, "electrique").map((node) => node.id), ["P1"]);
  assert.deepEqual(searchInfrastructure(nodes, "antenne").map((node) => node.id), ["T1"]);
  assert.deepEqual(searchInfrastructure(nodes, "rue").map((node) => node.id), ["R1"]);
  assert.deepEqual(searchInfrastructure(nodes, "république").map((node) => node.id), ["H1", "R1"]);
  assert.deepEqual(searchInfrastructure(nodes, "p1").map((node) => node.id), ["P1"]);
  assert.deepEqual(searchInfrastructure(nodes, "").map((node) => node.id), []);
});
