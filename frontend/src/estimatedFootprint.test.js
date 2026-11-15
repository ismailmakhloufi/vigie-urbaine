import test from "node:test";
import assert from "node:assert/strict";
import { buildEstimatedFootprint } from "./estimatedFootprint.js";

test("les sites proches forment une emprise, les sites distants restent séparés", () => {
  const infra = [
    { id: "H1", lat: 36.8, lon: 10.17 },
    { id: "W1", lat: 36.802, lon: 10.172 },
    { id: "H2", lat: 36.87, lon: 10.31 },
  ];
  const result = buildEstimatedFootprint(infra,
    [{ id: "H1", depth: 1 }, { id: "W1", depth: 2 }, { id: "H2", depth: 1 }]);
  assert.equal(result.groups.length, 2);
  assert.deepEqual(result.groups[0].ids, ["H1", "W1"]);
  assert.deepEqual(result.groups[1].ids, ["H2"]);
  assert.equal(result.groups[1].polygon.length, 4);
  assert.equal(result.uncertainty, "Modérée");
  assert.ok(result.groups[0].polygon.every(([lat, lon]) => Number.isFinite(lat) && Number.isFinite(lon)));
});

test("une position manquante ou une chaîne profonde augmente l'incertitude", () => {
  const result = buildEstimatedFootprint([{ id: "H1", lat: 36.8, lon: 10.17 }],
    [{ id: "H1", depth: 1 }, { id: "missing", depth: 4 }]);
  assert.equal(result.mappedCount, 1);
  assert.equal(result.missingCount, 1);
  assert.equal(result.uncertainty, "Élevée");
  assert.equal(buildEstimatedFootprint([], []).groups.length, 0);
});
