// Classement d'aide à la lecture, jamais une gravité constatée ni un état en base.
const SEVERITY_POINTS = { CRITICAL: 80, HIGH: 60, MEDIUM: 35, LOW: 10 };

export function prioritizeNotifications(items, infrastructure, nodesAtRisk, now = Date.now()) {
  const kinds = new Map(infrastructure.map((node) => [node.id, node.kind]));
  const hospitalEvents = new Set(nodesAtRisk.filter((node) => node.kind === "Hospital")
    .flatMap((node) => (node.sources || []).map((source) => source.event_id)));
  return items.map((item) => {
    if (item.state !== "NEW") return { ...item, priority: null };
    const age = Math.max(0, now - new Date(item.created_at).getTime()) || 0;
    const agePoints = Math.min(15, Math.floor(age / (15 * 60 * 1000)) * 3);
    const directHospital = kinds.get(item.location_id) === "Hospital";
    const eventId = item.category === "INCIDENT" && item.source_key?.startsWith("event:")
      ? item.source_key.slice(6) : null;
    const estimatedHospital = !directHospital && eventId && hospitalEvents.has(eventId);
    const score = (SEVERITY_POINTS[item.severity] ?? 10) + agePoints
      + (directHospital ? 20 : estimatedHospital ? 12 : 0);
    const reasons = [`Gravité enregistrée : ${item.severity}`];
    if (agePoints) reasons.push(`Ancienneté : +${agePoints}`);
    if (directHospital) reasons.push("Hôpital ciblé");
    else if (estimatedHospital) reasons.push("Hôpital potentiellement concerné (modèle)");
    return { ...item, priority: { level: score >= 80 ? "P1" : score >= 55 ? "P2" : "P3", score, reasons } };
  }).sort((a, b) => {
    if (a.priority && b.priority && a.priority.score !== b.priority.score) {
      return b.priority.score - a.priority.score;
    }
    const chronological = new Date(a.created_at) - new Date(b.created_at);
    return (a.priority ? chronological : -chronological) || a.id.localeCompare(b.id);
  });
}
