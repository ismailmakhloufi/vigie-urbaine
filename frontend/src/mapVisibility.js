export function roadVisible(node, selectedId, showRoadNetwork, replay = false) {
  return replay || showRoadNetwork || Boolean(node.status && node.status !== "CLEAR") || node.id === selectedId;
}

export function missionToHighlight(missions, selectedId, featuredId) {
  if (selectedId && missions.some((mission) => mission.mission_id === selectedId)) return selectedId;
  if (featuredId && missions.some((mission) => mission.mission_id === featuredId)) return featuredId;
  return missions[0]?.mission_id || null;
}

export function missionRouteVisible(missionId, highlightedId, showAll, replay = false) {
  return replay || showAll || missionId === highlightedId;
}
