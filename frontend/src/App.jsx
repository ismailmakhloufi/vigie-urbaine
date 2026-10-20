import { useEffect, useMemo, useState } from "react";
import MapView from "./components/MapView.jsx";
import {
  getInfrastructure,
  getRisk,
  getEvents,
  postEvent,
  postWhatif,
  resolveEvent,
} from "./api.js";

const TYPES_INCIDENT = [
  {
    type: "HEAVY_RAIN",
    label: "🌧 Pluie extrême",
    classe: "btn-pluie",
    cibles: ["Zone"],
    severite: "HIGH",
  },
  {
    type: "POWER_FAILURE",
    label: "⚡ Panne électrique",
    classe: "btn-panne",
    cibles: ["PowerStation"],
    severite: "CRITICAL",
  },
  {
    type: "ROAD_BLOCKED",
    label: "🚧 Route bloquée",
    classe: "btn-route",
    cibles: ["Road"],
    severite: "HIGH",
  },
  {
    type: "CYBER_ATTACK",
    label: "🛡 Cyberattaque",
    classe: "btn-cyber",
    cibles: ["Hospital", "PowerStation", "TelecomTower", "Warehouse", "Pharmacy"],
    severite: "HIGH",
  },
];

const EMOJI_KIND = {
  Hospital: "🏥",
  PowerStation: "⚡",
  TelecomTower: "📡",
  Warehouse: "📦",
  Pharmacy: "💊",
  Road: "🛣️",
  Zone: "🌐",
};

function RiskBadge({ risk }) {
  return <span className={`risk-badge risk-${(risk || "LOW").toLowerCase()}`}>{risk || "LOW"}</span>;
}

export default function App() {
  const [infra, setInfra] = useState([]);
  const [risque, setRisque] = useState(null);
  const [historique, setHistorique] = useState([]);
  const [cible, setCible] = useState(null);
  const [modeSimulation, setModeSimulation] = useState(false);
  const [vagues, setVagues] = useState([]);
  const [fantomes, setFantomes] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [toast, setToast] = useState(null);
  const [horloge, setHorloge] = useState("");
  const [erreur, setErreur] = useState(null);
  const [risqueSelectionne, setRisqueSelectionne] = useState(null);

  const refresh = async () => {
    try {
      const [infraData, riskData, eventsData] = await Promise.all([
        getInfrastructure(),
        getRisk(),
        getEvents(20),
      ]);
      setInfra(infraData);
      setRisque(riskData);
      setHistorique(eventsData);
      setErreur(null);
    } catch (exc) {
      setErreur(`Backend injoignable : ${exc.message}`);
    }
  };

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 4000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const update = () =>
      setHorloge(new Date().toLocaleTimeString("fr-FR", { hour12: false }));
    update();
    const t = setInterval(update, 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  useEffect(() => {
    if (!fantomes.length) return;
    const t = setTimeout(() => {
      setFantomes([]);
      setPrediction(null);
    }, 15000);
    return () => clearTimeout(t);
  }, [fantomes]);

  const nodesAtRisk = useMemo(
    () => [...(risque?.nodes_at_risk || [])].sort((a, b) => b.score - a.score),
    [risque]
  );

  const riskById = useMemo(
    () => Object.fromEntries(nodesAtRisk.map((node) => [node.id, node])),
    [nodesAtRisk]
  );

  const kpis = useMemo(() => {
    const incidentList = risque?.incident_list || [];
    const high = risque?.counts_by_class?.HIGH || 0;
    const critical = risque?.counts_by_class?.CRITICAL || 0;
    return {
      actifs: risque?.active_incidents ?? 0,
      critiques: high + critical,
      hospitals: nodesAtRisk.filter(
        (n) => n.kind === "Hospital" && ["HIGH", "CRITICAL"].includes(n.risk)
      ).length,
      profondeur: incidentList.reduce((m, i) => Math.max(m, i.max_depth || 0), 0),
    };
  }, [risque, nodesAtRisk]);

  const cityStatus = useMemo(() => {
    if ((risque?.counts_by_class?.CRITICAL || 0) > 0) return "CRITICAL";
    if ((risque?.counts_by_class?.HIGH || 0) > 0) return "DEGRADED";
    if ((risque?.active_incidents || 0) > 0) return "WATCH";
    return "STABLE";
  }, [risque]);

  const gererSelection = (node) => {
    setCible(node);
    setRisqueSelectionne(riskById[node.id] || null);
    setPrediction(null);
    setFantomes([]);
  };

  const ouvrirRisque = (node) => {
    const infrastructure = infra.find((item) => item.id === node.id);
    if (infrastructure) setCible(infrastructure);
    setRisqueSelectionne(node);
  };

  const declencher = async (definition) => {
    if (!cible) return;

    const contenu = {
      type: definition.type,
      severity: definition.severite,
      target_id: cible.id,
      description: `Déclenché depuis l'interface — cible ${cible.name}`,
      payload: { source: "urban-butterfly-ui" },
    };

    try {
      if (modeSimulation) {
        const predict = await postWhatif(contenu);
        setPrediction(predict);
        setFantomes(predict.impacts.map((i) => i.id));
        setToast(`🔮 What-if : ${predict.total_count} impact(s) prédit(s)`);
      } else {
        const resultat = await postEvent(contenu);
        setVagues(
          resultat.impact.impacts.map((i) => ({
            id: i.id,
            depth: i.depth,
            score: i.score,
          }))
        );
        setFantomes([]);
        setPrediction(null);
        setToast(`🦋 Incident propagé : ${resultat.impact.total_count} impact(s)`);
        await refresh();
      }
    } catch (exc) {
      setToast(`⛔ ${exc.message}`);
    }
  };

  const resoudre = async (id) => {
    try {
      await resolveEvent(id);
      await refresh();
      setToast("✅ Incident résolu, état restauré");
    } catch (exc) {
      setToast(`⛔ ${exc.message}`);
    }
  };

  return (
    <div className="app app-v2">
      <header className="header">
        <div className="logo">🦋</div>
        <div className="titre">
          <h1>Urban <span>Butterfly</span></h1>
          <p>Centre d'analyse des risques urbains en cascade</p>
        </div>

        <div className={`city-status status-${cityStatus.toLowerCase()}`}>
          <small>CITY STATUS</small>
          <strong>● {cityStatus}</strong>
        </div>

        <div className="horloge">
          Grand Tunis
          <b>{horloge}</b>
        </div>
      </header>

      <section className="kpi-strip">
        <div className="kpi-horizontal kpi-rouge">
          <span>Incidents actifs</span><strong>{kpis.actifs}</strong>
        </div>
        <div className="kpi-horizontal kpi-ambre">
          <span>Risques HIGH / CRITICAL</span><strong>{kpis.critiques}</strong>
        </div>
        <div className="kpi-horizontal kpi-violet">
          <span>Hôpitaux menacés</span><strong>{kpis.hospitals}</strong>
        </div>
        <div className="kpi-horizontal kpi-cyan">
          <span>Profondeur max</span><strong>{kpis.profondeur}</strong>
        </div>
      </section>

      <aside className="sidebar control-panel">
        <section>
          <div className="section-titre">Contrôle scénario</div>
          <div className="cible">
            {cible ? (
              <>
                <div className="target-title">
                  <span>{EMOJI_KIND[cible.kind] || "📍"}</span>
                  <div>
                    <b>{cible.name}</b>
                    <small>{cible.id} · {cible.kind}</small>
                  </div>
                </div>
                <div className="target-meta">
                  <span>Statut <b>{cible.status || "—"}</b></span>
                  <span>Criticité <b>{cible.criticality ?? "—"}/5</b></span>
                </div>
              </>
            ) : (
              <>
                <b>Aucune cible</b>
                <small>Cliquez sur un nœud de la carte.</small>
              </>
            )}
          </div>
        </section>

        <section>
          <div className="section-titre">Déclencher un incident</div>
          <div className="boutons-incident">
            {TYPES_INCIDENT.map((d) => (
              <button
                key={d.type}
                className={`btn ${d.classe}`}
                disabled={!cible || !d.cibles.includes(cible.kind)}
                onClick={() => declencher(d)}
              >
                {d.label}
              </button>
            ))}
          </div>
        </section>

        <section>
          <div
            className={`basculer-whatif ${modeSimulation ? "actif" : ""}`}
            role="button"
            tabIndex={0}
            onClick={() => {
              setModeSimulation((s) => !s);
              setFantomes([]);
              setPrediction(null);
            }}
          >
            <span>
              <span className="nom">MODE WHAT-IF</span>
              <small>Prévoir sans modifier la ville</small>
            </span>
            <span className={`interrupteur ${modeSimulation ? "on" : ""}`} />
          </div>
        </section>

        {prediction && (
          <section className="whatif-card">
            <div className="section-titre">Prédiction What-if</div>
            <div className="whatif-summary">
              <div><strong>{prediction.total_count}</strong><span>impacts</span></div>
              <div><strong>{prediction.max_depth}</strong><span>profondeur</span></div>
              <div>
                <strong>
                  {Math.max(0, ...prediction.impacts.map((i) => i.score))}
                </strong>
                <span>risque max</span>
              </div>
            </div>
            <div className="prediction-list">
              {prediction.impacts.slice(0, 6).map((impact) => (
                <div className="prediction-row" key={impact.id}>
                  <span>{EMOJI_KIND[impact.kind] || "📍"} {impact.name}</span>
                  <RiskBadge risk={impact.risk} />
                  <b>{impact.score}</b>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="active-incidents">
          <div className="section-titre">Incidents actifs</div>
          {(risque?.incident_list || []).length === 0 ? (
            <div className="empty-state">✓ Aucun incident actif</div>
          ) : (
            (risque?.incident_list || []).map((incident) => (
              <article className="incident-card" key={incident.event_id}>
                <div className="incident-head">
                  <span className="incident-type">{incident.type}</span>
                  <span>{incident.severity}</span>
                </div>
                <strong>{incident.target_id}</strong>
                <small>
                  {incident.total_count} impact(s) · profondeur {incident.max_depth}
                </small>
                <button onClick={() => resoudre(incident.event_id)}>Résoudre</button>
              </article>
            ))
          )}
        </section>
      </aside>

      <main className="map-zone">
        <MapView
          infra={infra}
          cibleId={cible?.id}
          onSelection={gererSelection}
          vaguesCascades={vagues}
          fantomes={fantomes}
          riskById={riskById}
        />
        {toast && <div className="toast">{toast}</div>}
      </main>

      <aside className="risk-center">
        <div className="risk-center-header">
          <div>
            <small>LIVE ANALYSIS</small>
            <h2>Risk Center</h2>
          </div>
          <span>{nodesAtRisk.length} nœuds</span>
        </div>

        {risqueSelectionne ? (
          <section className="risk-focus">
            <div className="risk-focus-top">
              <div className="risk-score-large">{risqueSelectionne.score}</div>
              <div>
                <RiskBadge risk={risqueSelectionne.risk} />
                <h3>{risqueSelectionne.name}</h3>
                <small>{risqueSelectionne.kind} · {risqueSelectionne.id}</small>
              </div>
            </div>
            <div className="risk-meter">
              <i style={{ width: `${risqueSelectionne.score}%` }} />
            </div>
            <div className="section-titre">Pourquoi ce risque ?</div>
            <ul className="risk-reasons">
              {(risqueSelectionne.reasons || []).map((reason, i) => (
                <li key={i}>{reason}</li>
              ))}
            </ul>
          </section>
        ) : (
          <div className="risk-hint">
            Sélectionnez un risque ci-dessous pour afficher son explication.
          </div>
        )}

        <section className="risk-list-wrap">
          <div className="section-titre">Priorités</div>
          <div className="risk-list">
            {nodesAtRisk.length === 0 ? (
              <div className="empty-state">Aucun risque calculé actuellement.</div>
            ) : (
              nodesAtRisk.slice(0, 10).map((node, index) => (
                <button
                  className={`risk-row ${risqueSelectionne?.id === node.id ? "selected" : ""}`}
                  key={node.id}
                  onClick={() => ouvrirRisque(node)}
                >
                  <span className="rank">#{index + 1}</span>
                  <span className="risk-icon">{EMOJI_KIND[node.kind] || "📍"}</span>
                  <span className="risk-name">
                    <b>{node.name}</b>
                    <small>{node.id} · niveau {node.depth}</small>
                  </span>
                  <RiskBadge risk={node.risk} />
                  <strong className="risk-score">{node.score}</strong>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="history-mini">
          <div className="section-titre">Derniers événements</div>
          {historique.slice(0, 5).map((ev, i) => (
            <div className="history-row" key={ev.id || i}>
              <span>{new Date(ev.timestamp).toLocaleTimeString("fr-FR", { hour12: false })}</span>
              <b>{ev.type}</b>
              <span>→ {ev.target_id}</span>
              <i className={ev.status === "RESOLVED" ? "resolved" : "active"} />
            </div>
          ))}
        </section>
      </aside>

      <footer className="footer">
        <span className={erreur ? "dot-error" : "dot-verte"} />
        {erreur ? (
          <span className="footer-error">{erreur}</span>
        ) : (
          <span>FastAPI · Neo4j · MongoDB · Open-Meteo</span>
        )}
        <span className="footer-right">Urban Butterfly · NoSQL Digital Twin</span>
      </footer>
    </div>
  );
}
