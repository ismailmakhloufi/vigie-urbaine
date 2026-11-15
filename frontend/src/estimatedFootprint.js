// Enveloppes de VISUALISATION autour des sites modélisés : pas des frontières
// physiques de dégâts. Groupes séparés pour ne pas colorier toute la ville.
const METERS_PER_DEGREE = 111_000;
const GROUP_DISTANCE_METERS = 2_500;
const DISPLAY_PADDING_METERS = 200;

function hull(points) {
  const sorted = [...points].sort((a, b) => a.x - b.x || a.y - b.y);
  const cross = (a, b, c) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
  const half = (list) => {
    const out = [];
    for (const point of list) {
      while (out.length >= 2 && cross(out.at(-2), out.at(-1), point) <= 0) out.pop();
      out.push(point);
    }
    return out;
  };
  return [...half(sorted).slice(0, -1), ...half(sorted.reverse()).slice(0, -1)];
}

export function buildEstimatedFootprint(infra, impacts) {
  const positions = new Map(infra.map((node) => [node.id, node]));
  const latitude = impacts.map((impact) => positions.get(impact.id)?.lat)
    .find((lat) => typeof lat === "number" && Number.isFinite(lat)) ?? 36.8;
  const lonScale = METERS_PER_DEGREE * Math.cos(latitude * Math.PI / 180);
  const plotted = [];
  for (const impact of impacts) {
    const node = positions.get(impact.id);
    if (!node || !Number.isFinite(node.lat) || !Number.isFinite(node.lon)
        || Math.abs(node.lat) > 90 || Math.abs(node.lon) > 180) continue;
    plotted.push({ id: impact.id, x: node.lon * lonScale, y: node.lat * METERS_PER_DEGREE });
  }
  const groups = [];
  const remaining = new Set(plotted);
  while (remaining.size) {
    const group = [];
    const queue = [remaining.values().next().value];
    remaining.delete(queue[0]);
    while (queue.length) {
      const current = queue.pop();
      group.push(current);
      for (const other of remaining) {
        if (Math.hypot(current.x - other.x, current.y - other.y) <= GROUP_DISTANCE_METERS) {
          remaining.delete(other);
          queue.push(other);
        }
      }
    }
    const corners = group.flatMap(({ x, y }) => [
      { x: x - DISPLAY_PADDING_METERS, y: y - DISPLAY_PADDING_METERS },
      { x: x - DISPLAY_PADDING_METERS, y: y + DISPLAY_PADDING_METERS },
      { x: x + DISPLAY_PADDING_METERS, y: y - DISPLAY_PADDING_METERS },
      { x: x + DISPLAY_PADDING_METERS, y: y + DISPLAY_PADDING_METERS },
    ]);
    groups.push({ ids: group.map(({ id }) => id), polygon: hull(corners).map(({ x, y }) =>
      [y / METERS_PER_DEGREE, x / lonScale]) });
  }
  const missingCount = impacts.length - plotted.length;
  const maxDepth = Math.max(0, ...impacts.map((impact) => impact.depth || 0));
  return {
    groups, mappedCount: plotted.length, missingCount,
    uncertainty: !impacts.length ? "Non quantifiable"
      : missingCount || maxDepth >= 3 ? "Élevée" : "Modérée",
    reason: missingCount ? `${missingCount} site(s) sans coordonnées` :
      maxDepth >= 3 ? "Chaînes de dépendance longues" : "Modèle non calibré sur des dommages réels",
  };
}
