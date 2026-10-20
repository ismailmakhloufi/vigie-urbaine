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
