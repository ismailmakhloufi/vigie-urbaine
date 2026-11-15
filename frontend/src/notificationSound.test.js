import test from "node:test";
import assert from "node:assert/strict";
import { recordIncoming, SOUND_LEDGER_KEY } from "./notificationSound.js";

function storage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
}
const notification = (id, category = "INCIDENT", severity = "CRITICAL") =>
  ({ id, category, severity, state: "NEW" });

test("première ouverture silencieuse, nouvelle alerte unique après rechargement", () => {
  const store = storage();
  assert.deepEqual(recordIncoming(store, [notification("old")]), []);
  assert.deepEqual(recordIncoming(store, [notification("new"), notification("new"), notification("old")]).map((n) => n.id), ["new"]);
  assert.deepEqual(recordIncoming(store, [notification("new"), notification("old")]), []);
  assert.deepEqual(recordIncoming(store, [notification("missed"), notification("new")]).map((n) => n.id), ["missed"]);
  assert.equal(JSON.parse(store.getItem(SOUND_LEDGER_KEY)).seen.includes("missed"), true);
});

test("les arrivées sans urgence restent silencieuses et ne sont pas rejouées", () => {
  const store = storage();
  recordIncoming(store, []);
  assert.deepEqual(recordIncoming(store, [notification("arrived", "MISSION", "LOW")]), []);
  assert.deepEqual(recordIncoming(store, [notification("arrived", "MISSION", "HIGH")]), []);
  assert.deepEqual(recordIncoming(store, [notification("call", "CALL", "MEDIUM")]).map((n) => n.id), ["call"]);
});
