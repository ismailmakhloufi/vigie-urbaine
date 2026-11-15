// Le suivi est local au navigateur : une première ouverture initialise un état
// silencieux ; les visites suivantes annoncent seulement les nouvelles clés.
export const SOUND_LEDGER_KEY = "urban-butterfly:notification-sound:v1";

export const shouldSound = (item) => item.state === "NEW" && (
  item.category === "CALL" ||
  item.category === "INCIDENT" && ["HIGH", "CRITICAL"].includes(item.severity) ||
  item.category === "MISSION" && item.severity === "HIGH"
);

export function recordIncoming(storage, items) {
  let raw = null;
  try { raw = storage.getItem(SOUND_LEDGER_KEY); } catch { /* stockage indisponible */ }
  let saved = null;
  try { saved = raw && JSON.parse(raw); } catch { /* état ancien illisible */ }
  const initial = !Array.isArray(saved?.seen);
  const seen = new Set(initial ? [] : saved.seen);
  const fresh = [];
  for (const item of items) {
    if (!initial && !seen.has(item.id) && shouldSound(item)) fresh.push(item);
    seen.add(item.id);
  }
  const updated = { seen: [...seen].slice(-500) };
  try { storage.setItem(SOUND_LEDGER_KEY, JSON.stringify(updated)); } catch { /* mode privé */ }
  return fresh;
}
