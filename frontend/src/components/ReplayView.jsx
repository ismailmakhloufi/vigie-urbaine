import { useEffect, useMemo, useState } from "react";
import MapView from "./MapView.jsx";
import { getReplaySnapshot, getReplaySnapshots } from "../api.js";
import { ETYPES_FR, NATURES_FR, STATUTS_FR, NIVEAU } from "../libelles.js";

const STATUT_MISSION = { EN_ROUTE: "EN ROUTE", DIVERTED: "DÉROUTÉE", BLOCKED: "BLOQUÉE", ARRIVED: "ARRIVÉE", CANCELLED: "ANNULÉE" };
const STATUT_APPEL = { DISPATCHED: "ASSIGNÉ", PENDING: "ATTENTE VÉHICULE", NO_VEHICLE: "AUCUN VÉHICULE", ROUTE_UNAVAILABLE: "ACCÈS INDISPONIBLE" };

function horodatage(value) {
  return new Date(value).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "medium" });
}

export default function ReplayView({ infrastructure, onClose }) {
  const [timeline, setTimeline] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getReplaySnapshots().then(({ snapshots }) => {
      if (!active) return;
      const ordered = [...snapshots].reverse();
      setTimeline(ordered);
      setSelectedId(ordered.at(-1)?.id || null);
      setLoading(false);
    }).catch((exc) => { if (active) { setError(exc.message); setLoading(false); } });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    setSnapshot(null);
    setSelectedNode(null);
    setError(null);
    getReplaySnapshot(selectedId).then((data) => {
      if (active) setSnapshot(data);
    }).catch((exc) => { if (active) setError(exc.message); });
    return () => { active = false; };
  }, [selectedId]);

  const index = timeline.findIndex((item) => item.id === selectedId);
  const riskById = useMemo(() => Object.fromEntries(
    (snapshot?.risk?.nodes_at_risk || []).map((node) => [node.id, node])
  ), [snapshot]);
  const archivedInfra = useMemo(() => {
    if (!snapshot) return [];
    const statuses = snapshot.infrastructure_status || {};
    return infrastructure.filter((item) => Object.hasOwn(statuses, item.id))
      .map((item) => ({ ...item, status: statuses[item.id] }));
  }, [infrastructure, snapshot]);
  const counts = snapshot?.risk?.counts_by_class || {};
  const node = selectedNode ? riskById[selectedNode.id] : null;

  return (
    <div className="replay-screen">
      <header className="replay-header">
        <div className="replay-brand"><h1>Vigie <span>Urbaine</span></h1><p>Centre d'analyse des risques urbains en cascade</p></div>
        <div className="replay-heading"><small>CONSULTATION EN LECTURE SEULE</small><h2>Relecture de crise</h2></div>
        <button type="button" onClick={onClose}>← Retour au direct</button>
      </header>
      <div className="replay-timeline">
        <label htmlFor="replay-range">Instant enregistré <b>{index >= 0 ? index + 1 : 0} / {timeline.length}</b></label>
        <button disabled={index <= 0} onClick={() => setSelectedId(timeline[index - 1].id)}>← Précédent</button>
        <input id="replay-range" type="range" min="0" max={Math.max(0, timeline.length - 1)}
          value={Math.max(0, index)} disabled={timeline.length < 2}
          onChange={(event) => setSelectedId(timeline[Number(event.target.value)].id)} />
        <button disabled={index < 0 || index >= timeline.length - 1}
          onClick={() => setSelectedId(timeline[index + 1].id)}>Suivant →</button>
        <strong>{snapshot ? horodatage(snapshot.captured_at) : "—"}</strong>
      </div>
      <div className="replay-warning">
        <strong>Archive en lecture seule</strong>
        <span>Les données ne sont pas enregistrées simultanément. Géométrie actuelle ; statuts et scores archivés.
        {snapshot && ` Fenêtre de capture : ${Math.max(0, (new Date(snapshot.captured_at) - new Date(snapshot.started_at)) / 1000).toFixed(1)} s.`}
        {" "}Conservation : 24 h ; les archives antérieures ne sont pas reconstituées.</span>
      </div>
      {error && <div className="replay-empty" role="alert"><div><strong>Archive indisponible</strong><p>{error}</p></div></div>}
      {!error && loading && <div className="replay-empty" role="status"><div><strong>Chargement des archives…</strong></div></div>}
      {!error && !loading && timeline.length === 0 && <div className="replay-empty"><div><strong>Aucun instantané enregistré</strong><p>Les captures apparaîtront ici lorsque l'enregistrement de la simulation sera actif.</p></div></div>}
      {!error && timeline.length > 0 && !snapshot && <div className="replay-empty" role="status"><div><strong>Lecture de l'instantané…</strong></div></div>}
      {snapshot && !error && (
        <div className="replay-content">
          <div className="replay-map">
            <MapView infra={archivedInfra} riskById={riskById} replay
              cibleId={selectedNode?.id} onSelection={setSelectedNode} />
          </div>
          <aside className="replay-detail">
            <div className="section-titre">État enregistré · {horodatage(snapshot.captured_at)}</div>
            <div className="replay-stats">
              <span><b>{snapshot.risk.active_incidents}</b> incidents</span>
              <span><b>{(counts.HIGH || 0) + (counts.CRITICAL || 0)}</b> risques élevés/critiques</span>
              <span><b>{snapshot.vehicles.length}</b> véhicules</span>
            </div>
            {selectedNode && <section className="replay-focus">
              <div className="section-titre">Lieu sélectionné</div>
              <b>{selectedNode.name} · {NATURES_FR[selectedNode.kind] || selectedNode.kind}</b>
              <p>Statut enregistré : {STATUTS_FR[selectedNode.status] || selectedNode.status || "inconnu"}</p>
              <p>{node ? `Risque ${NIVEAU(node.risk)} · ${node.score}/100` : "Aucun risque calculé pour ce lieu"}</p>
              {(node?.sources || []).map((source) => <small key={source.event_id}>
                {ETYPES_FR[source.type] || source.type} · {source.target_id} · score {source.score}
              </small>)}
            </section>}
            <div className="section-titre">Incidents archivés</div>
            {snapshot.risk.incident_list.length === 0 && <div className="empty-state">Aucun incident au moment de cette capture.</div>}
            {(snapshot.risk.incident_list || []).map((item) => <div className="replay-item" key={item.event_id}>
              <b>{ETYPES_FR[item.type] || item.type} · {item.target_id}</b>
              <span>{item.total_count} impacts · profondeur {item.max_depth}</span>
            </div>)}
            <div className="section-titre">Missions observées</div>
            {snapshot.missions.length === 0 && <div className="empty-state">Aucune mission enregistrée.</div>}
            {snapshot.missions.map((item) => <div className="replay-item" key={item.mission_id}>
              <b>{item.mission_id} · {item.vehicle || "—"}</b>
              <span>{item.origin_id} → {item.destination_id} · {STATUT_MISSION[item.status] || item.status}</span>
            </div>)}
            <div className="section-titre">Derniers appels observés</div>
            {snapshot.calls.map((item) => <div className="replay-item" key={item.call_id}>
              <b>{item.call_id} · {item.destination_id}</b>
              <span>{STATUT_APPEL[item.status] || item.status} · {item.assigned_vehicle || item.queue_reason || "—"}</span>
            </div>)}
          </aside>
        </div>
      )}
    </div>
  );
}
