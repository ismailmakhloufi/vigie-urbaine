export async function apiFetch(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.message || detail;
    } catch {
      /* réponse non JSON */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const getInfrastructure = () => apiFetch("/infrastructure");
export const getRisk = () => apiFetch("/risk");
export const getEvents = (limit = 20) => apiFetch(`/events?limit=${limit}`);

export const postEvent = (body) =>
  apiFetch("/events", { method: "POST", body: JSON.stringify(body) });

export const postWhatif = (body) =>
  apiFetch("/whatif", { method: "POST", body: JSON.stringify(body) });

export const resolveEvent = (id) =>
  apiFetch(`/events/${id}/resolve`, { method: "POST" });

export const getEventImpact = (id) =>
  apiFetch(`/events/${id}/impact`);

export const getEventRecommendations = (id) =>
  apiFetch(`/events/${id}/recommendations`);

export const aiAsk = (question) =>
  apiFetch("/ai/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });

export const aiBriefing = () =>
  apiFetch("/ai/briefing", { method: "POST" });

export const getMissions = () => apiFetch("/missions");

export const cancelMission = (missionId) =>
  apiFetch(`/missions/${missionId}/cancel`, { method: "POST" });

// ----- console dispatcher -----

export const getFleet = () => apiFetch("/fleet");

export const getCalls = (limit = 8) =>
  apiFetch(`/integration/calls?limit=${limit}`);

export const postRandomCall = () =>
  apiFetch("/integration/calls/random", { method: "POST" });

export const getDemo = () => apiFetch("/integration/demo");

export const postDemo = (action) =>
  apiFetch("/integration/demo", {
    method: "POST",
    body: JSON.stringify({ action }),
  });

export const postRouteOptions = (origin_id, destination_id, profile = "AMBULANCE") =>
  apiFetch("/route-options", {
    method: "POST",
    body: JSON.stringify({ origin_id, destination_id, profile }),
  });

export const postCorridor = (missionId, minutes = 3) =>
  apiFetch(`/missions/${missionId}/corridor`, {
    method: "POST",
    body: JSON.stringify({ minutes }),
  });

export const postRadio = (missionId, author, text) =>
  apiFetch(`/missions/${missionId}/radio`, {
    method: "POST",
    body: JSON.stringify({ author, text }),
  });

export const postChooseRoute = (missionId, variant) =>
  apiFetch(`/missions/${missionId}/choose-route`, {
    method: "POST",
    body: JSON.stringify({ variant }),
  });
