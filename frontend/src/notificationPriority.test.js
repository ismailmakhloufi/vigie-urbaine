import test from "node:test";
import assert from "node:assert/strict";
import { prioritizeNotifications } from "./notificationPriority.js";

const now = Date.parse("2026-11-15T12:00:00Z");
const item = (id, severity, minutes, location_id, extra = {}) => ({
  id, severity, state: "NEW", category: "INCIDENT", location_id,
  created_at: new Date(now - minutes * 60000).toISOString(), ...extra,
});

test("gravité, ancienneté et hôpital estimé classent sans changer les faits", () => {
  const items = [
    item("low", "LOW", 120, "R1"),
    item("hospital", "HIGH", 30, "R1", { source_key: "event:e1" }),
    item("critical", "CRITICAL", 0, "R2"),
    item("direct", "MEDIUM", 0, "H1"),
  ];
  const hospitals = [{ kind: "Hospital", sources: [{ event_id: "e1" }] }];
  const ranked = prioritizeNotifications(items, [{ id: "H1", kind: "Hospital" }], hospitals, now);
  assert.deepEqual(ranked.map((n) => n.id), ["critical", "hospital", "direct", "low"]);
  assert.equal(ranked[1].priority.level, "P2");
  assert.match(ranked[1].priority.reasons.join(" "), /potentiellement.*modèle/);
  assert.equal(items[1].priority, undefined);
  assert.equal(items[1].state, "NEW");
});

test("un incident clos ou une source sans lien ne bénéficie pas d'un risque actif", () => {
  const rows = prioritizeNotifications([
    item("closed", "CRITICAL", 200, "R1", { state: "RESOLVED", source_key: "event:e1" }),
    item("other", "HIGH", 0, "R1", { source_key: "event:e2" }),
  ], [], [{ kind: "Hospital", sources: [{ event_id: "e1" }] }], now);
  assert.equal(rows[0].priority, null);
  assert.equal(rows[1].priority.score, 60);
});
