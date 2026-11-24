import test from "node:test";
import assert from "node:assert/strict";
import { propagationExplanation } from "./propagationExplanation.js";

test("un chemin via dépôt annonce un retard possible et non une panne", () => {
  const info = propagationExplanation({ type: "ROAD_BLOCKED", chain: [{ kind: "Road" }, { kind: "Warehouse" }, { kind: "Pharmacy" }] });
  assert.match(info.effect, /Retard d'approvisionnement possible/);
  assert.match(info.uncertainty, /non validé/);
});

test("la pluie dans une zone ne prouve pas une inondation locale", () => {
  assert.match(propagationExplanation({ type: "HEAVY_RAIN" }).effect, /ni inondation/);
});
