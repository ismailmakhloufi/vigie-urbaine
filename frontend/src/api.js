export async function apiFetch(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    if (res.status === 401 && path !== "/auth/login") {
      window.dispatchEvent(new Event("ub-session-expired"));
    }
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

export const getSecurityConfig = () => apiFetch("/auth/config");
export const getCurrentUser = () => apiFetch("/auth/me");
export const signIn = (username, password) => apiFetch("/auth/login", {
  method: "POST", body: JSON.stringify({ username, password }),
});
export const signOut = () => apiFetch("/auth/logout", { method: "POST" });
export const getAudit = () => apiFetch("/auth/audit?limit=8");
export const getReplaySnapshots = () => apiFetch("/replay?limit=240");
export const getReplaySnapshot = (id) => apiFetch(`/replay/${encodeURIComponent(id)}`);
export const getNotifications = (state = "NEW") =>
  apiFetch(`/notifications?state=${encodeURIComponent(state)}&limit=500`);
export const acknowledgeNotification = (id) =>
  apiFetch(`/notifications/${encodeURIComponent(id)}/acknowledge`, { method: "POST" });

export const getInfrastructure = () => apiFetch("/infrastructure");
export const getRisk = () => apiFetch("/risk");
export const getInterventionPreview = (eventId) =>
  apiFetch(`/risk/intervention/${encodeURIComponent(eventId)}`);
export const getDecisionRanking = () => apiFetch("/risk/decisions");
export const getRiskEvolution = () => apiFetch("/risk/evolution?limit=8");
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

export const getStream = () => apiFetch("/integration/stream");
export const getSimulationActivity = (before = null) => apiFetch(
  `/integration/activity?limit=60${before
    ? `&before_at=${encodeURIComponent(before.at)}&before_id=${encodeURIComponent(before.id)}` : ""}`
);
export const getSourceHealth = () => apiFetch("/integration/sources");

export const postStreamAction = (action) =>
  apiFetch("/integration/stream", {
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
