// Le backend peut assembler deux routes distantes sans géométrie de liaison.
// Ne pas dessiner de droite inventée entre ces points (notamment sur le lac).
export function splitRouteAtGaps(points, maxGapKm = 2) {
  const segments = [];
  let current = [];

  for (const point of points) {
    const previous = current.at(-1);
    if (!Array.isArray(point) || point.length < 2 || !point.every(Number.isFinite)) {
      if (current.length > 1) segments.push(current);
      current = [];
      continue;
    }

    if (previous) {
      const latDiff = (point[0] - previous[0]) * 111;
      const lonDiff = (point[1] - previous[1]) * 111 * Math.cos(previous[0] * Math.PI / 180);
      if (Math.hypot(latDiff, lonDiff) > maxGapKm) {
        if (current.length > 1) segments.push(current);
        current = [];
      }
    }
    current.push(point);
  }

  if (current.length > 1) segments.push(current);
  return segments;
}
