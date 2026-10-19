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
  { type: "HEAVY_RAIN", label: "🌧 Pluie extrême", classe: "btn-pluie", zoneSeule: true },
  { type: "POWER_FAILURE", label: "⚡ Panne électrique", classe: "btn-panne" },
  { type: "ROAD_BLOCKED", label: "🚧 Route bloquée", classe: "btn-route" },
  { type: "CYBER_ATTACK", label: "📡 Cyberattaque", classe: "btn-cyber" },
];

export default function App() {
  const [infra, setInfra] = useState([]);
  const [risque, setRisque] = useState(null);
  const [historique, setHistorique] = useState([]);
  const [cible, setCible] = useState(null);
  const [modeSimulation, setModeSimulation] = useState(false);
  const [vagues, setVagues] = useState([]);
  const [fantomes, setFantomes] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [toast, setToast] = useState(null);
  const [horloge, setHorloge] = useState("");
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    const refresh = async () => {
      try {
        setInfra(await getInfrastructure());
        setRisque(await getRisk());
        setHistorique(await getEvents(12));
      } catch (exc) {
        setErreur(`Backend injoignable : ${exc.message}`);
      }
    };
    refresh();
    const timer = setInterval(refresh, 4000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const t = setInterval(
      () => setHorloge(new Date().toLocaleTimeString("fr-FR", { hour12: false })),
      1000
    );
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  const kpis = useMemo(() => {
    if (!risque) return null;
    const noeuds = risque.nodes_at_risk || [];
    return {
      actifs: risque.active_incidents,
      critiques: (risque.counts_by_class?.CRITICAL ?? 0) + (risque.counts_by_class?.HIGH ?? 0),
      hospitals: noeuds.filter((n) => n.kind === "Hospital").length,
      profondeur: risque.incident_list.reduce((m, i) => Math.max(m, i.max_depth), 0),
    };
  }, [risque]);

  const declencher = async (definition) => {
    if (!cible) return;
    const contenu = {
      type: definition.type,
      severity: definition.type === "HEAVY_RAIN" ? "CYBER" in definition ? "HIGH" : "HIGH" : "CRITICAL",
      target_id: cible.id,
      description: `Déclenché depuis l'interface — cible ${cible.name}`,
    };
    try {
      if (modeSimulation) {
        const predict = await postWhatif(contenu);
        setPrediction(predict);
        setFantomes(predict.impacts.map((i) => i.id));
        setToast(`🔮 Prédiction What-if calculée (côté lecture seule)`);
      } else {
        const resultat = await postEvent(contenu);
        setVagues(
          resultat.impact.impacts.map((i) => ({ id: i.id, depth: i.depth, score: i.score }))
        );
        setFantomes(null);
        setPrediction(null);
        setToast(`🦋 Incident propagé : ${resultat.impact.total_count} nœud(s) avec impact`);
      }
    } catch (exc) {
      setToast(`⛔ ${exc.message}`);
    }
  };

  useEffect(() => {
    if (!fantomes) return;
    const t = setTimeout(() => {
      setFantomes(null);
      setPrediction(null);
    }, 12000);
    return () => clearTimeout(t);
  }, [fantomes]);

  const gererSelection = (node) => {
    setCible(node);
    setPrediction(null);
    setFantomes(null);
  };

  const resoudre = async (id) => {
    try {
      await resolveEvent(id);
      setRisque(await getRisk());
      setToast("✅ Incident résolu, état restauré");
    } catch (exc) {
      setToast(`⛔ ${exc.message}`);
    }
  };

  const arrose = (node) => node.kind === "Zone" ? "zone" : node.kind;

  return (
    <div className="app">
      <header className="header">
        <div className="logo">🦋</div>
        <div className="titre">
          <h1>
            Urban <span>Butterfly</span>
          </h1>
          <p>Simulateur intelligent de risques en cascade — "Un événement, mille conséquences"</p>
        </div>
        <div className="horloge">
          Ville de <b>Tunis</b>
          <b>{horloge}</b>
        </div>
      </header>

      <aside className="sidebar">
        <section>
          <div className="section-titre">Bulletin de santé ville</div>
          <div className="kpis">
            <div className="kpi kpi-rouge">
              <div className="valeur">{kpis?.actifs ?? "—"}</div>
              <div className="libelle">Incidents actifs</div>
            </div>
            <div className="kpi kpi-ambre">
              <div className="valeur">{kpis?.critiques ?? "—"}</div>
              <div className="libelle">Nœuds à haut risque</div>
            </div>
            <div className="kpi kpi-violet">
              <div className="valeur">{kpis?.hospitals ?? "—"}</div>
              <div className="libelle">Hôpitaux menacés</div>
            </div>
            <div className="kpi kpi-cyan">
              <div className="valeur">{kpis?.profondeur ?? "—"}</div>
              <div className="libelle">Profondeur cascade</div>
            </div>
          </div>
        </section>

        <section>
          <div className="section-titre">Cible</div>
          <div className="cible">
            {cible ? (
              <>
                Cible verrouillée : <b>{cible.name}</b>
                <small style={{ display: "block", color: "var(--ink-dim)" }}>
                  {arrose(cible)} — clic sur un autre pin pour changer
                </small>
              </>
            ) : (
              <>
                <b>Aucune cible</b>
                <div style={{ color: "var(--ink-dim)" }}>
                  Cliquez sur un nœud de la carte pour le cibler
                </div>
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
                disabled={!cible || (d.zoneSeule && cible.kind !== "Zone")}
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
              setFantomes(null);
              setPrediction(null);
            }}
          >
            <span>
              <span className="nom">MODE SIMULATION</span>
              <small style={{ display: "block", color: "var(--ink-dim)" }}>
                Prévoir l'impact sans rien modifier
              </small>
            </span>
            <span className={`interrupteur ${modeSimulation ? "on" : ""}`} />
          </div>
        </section>

        {prediction && (
          <section>
            <div className="section-titre">🔮 Prédiction what-if</div>
            <div className="prediction">
              {prediction.impacts.length === 0 ? (
                <>Aucune conséquence directe détectée.</>
              ) : (
                prediction.impacts.map((impact) => (
                  <div className="rang" key={impact.id}>
                    <span>
                      {impact.name}
                      <small style={{ color: "var(--ink-dim)" }}> (niveau {impact.depth})</small>
                    </span>
                    <b style={{ color: impact.risk === "CRITICAL" ? "var(--red)" : impact.risk === "HIGH" ? "var(--amber)" : "var(--cyan)" }}>
                      {impact.score}/100
                    </b>
                  </div>
                ))
              )}
            </div>
          </section>
        )}

        <section>
          <div className="section-titre">Incidents actifs</div>
          {(risque?.incident_list || []).length === 0 ? (
            <p style={{ color: "var(--ink-dim)", fontSize: 12.5 }}>
              Situation calme dans la ville. Les capteurs virtuels veillent...
            </p>
          ) : (
            (risque?.incident_list || []).map((incident) => (
              <div className="incident" key={incident.event_id}>
                <span className="tag">{incident.type}</span>
                <div>
                  {incident.target_id}
                  <small>prof. {incident.max_depth} · {incident.total_count} nœuds</small>
                </div>
                <button className="btn-resoudre" onClick={() => resoudre(incident.event_id)}>
                  Résoudre
                </button>
              </div>
            ))
          )}
        </section>

        <section>
          <div className="section-titre">Historique (MongoDB)</div>
          {historique.length === 0 ? (
            <p style={{ color: "var(--ink-dim)", fontSize: 12.5 }}>Aucun événement encore.</p>
          ) : (
            historique.slice(0, 8).map((ev, i) => (
              <div key={i} style={{ fontSize: 11.5, color: "var(--ink-dim)", marginBottom: 4, fontFamily: "var(--font-mono)" }}>
                {new Date(ev.timestamp).toLocaleTimeString("fr-FR", { hour12: false })} — {ev.type} → {ev.target_id}
                {ev.status === "RESOLVED" ? " ✅" : " 🔴"}
              </div>
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
          fantomes={fantomes || []}
        />
        {toast && <div className="toast">{toast}</div>}
      </main>

      <footer className="footer">
        <span className="dot-verte" />
        {erreur ? <span style={{ color: "var(--red)" }}>{erreur}</span> : (
          <span>API FastAPI — Neo4j graphe · MongoDB historique · météo Open-Meteo (réelle)</span>
        )}
        <span style={{ marginLeft: "auto" }}>Urban Butterfly v0.1 — projet NoSQL</span>
      </footer>
    </div>
  );
}
