import test from "node:test";
import assert from "node:assert/strict";
import { roadVisible, missionToHighlight, missionRouteVisible } from "./mapVisibility.js";

test("les routes saines sont masquées sauf sélection, mode réseau ou relecture", () => {
  const road = { id: "R1", status: "CLEAR" };
  assert.equal(roadVisible(road, null, false), false);
  assert.equal(roadVisible(road, "R1", false), true);
  assert.equal(roadVisible(road, null, true), true);
  assert.equal(roadVisible(road, null, false, true), true);
  assert.equal(roadVisible({ id: "R2", status: "BLOCKED" }, null, false), true);
});

test("une seule mission en évidence, l'ambulance guidée prioritaire", () => {
  const missions = [{ mission_id: "M-1" }, { mission_id: "M-2" }];
  assert.equal(missionToHighlight(missions, null, "M-2"), "M-2");
  assert.equal(missionToHighlight(missions, "M-1", "M-2"), "M-1");
  assert.equal(missionToHighlight(missions, "M-9", "M-2"), "M-2");
  assert.equal(missionToHighlight(missions, null, null), "M-1");
  assert.equal(missionRouteVisible("M-1", "M-2", false), false);
  assert.equal(missionRouteVisible("M-2", "M-2", false), true);
  assert.equal(missionRouteVisible("M-1", "M-2", true), true);
  assert.equal(missionRouteVisible("M-1", "M-2", false, true), true);
});
