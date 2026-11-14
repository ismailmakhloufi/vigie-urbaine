import { useEffect, useMemo, useRef, useState } from "react";
import MapView from "./components/MapView.jsx";
import {
  NATURES_FR,
  PROFILS_FR,
  NIVEAUX_FR,
  ETYPES_FR,
  ETATS_VILLE_FR,
  NIVEAU,
} from "./libelles.js";
import {
  getInfrastructure,
  getRisk,
  getEvents,
  getEventImpact,
  getEventRecommendations,
  aiAsk,
  aiBriefing,
  postEvent,
  postWhatif,
  resolveEvent,
  getMissions,
  getFleet,
  getCalls,
  getStream,
  postRouteOptions,
  postCorridor,
  postRadio,
  postChooseRoute,
  cancelMission,
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

const STATUS_MISSION = {
  EN_ROUTE: { label: "EN ROUTE", classe: "m-en-route" },
  DIVERTED: { label: "DÉROUTÉE", classe: "m-diverted" },
  BLOCKED: { label: "BLOQUÉE", classe: "m-blocked" },
  ARRIVED: { label: "ARRIVÉE", classe: "m-arrived" },
  CANCELLED: { label: "ANNULÉE", classe: "m-cancelled" },
};

const STATUT_FLOTTE = {
  AVAILABLE: { label: "DISPO", classe: "f-dispo" },
  ON_MISSION: { label: "EN MISSION", classe: "f-mission" },
  RETURNING: { label: "RETOUR BASE", classe: "f-retour" },
  OUT_OF_SERVICE: { label: "HORS SERVICE", classe: "f-hs" },
};

const EMOJI_TYPE = {
  AMBULANCE: "🚑",
  SUPPLY: "🚚",
  NORMAL: "🚙",
};

const EMOJI_VEHICULE = {
  MEDICAL: "🚑",
  AMBULANCE: "🚑",
  SUPPLY: "🚚",
};

function RiskBadge({ risk }) {
  return (
    <span className={`risk-badge risk-${(risk || "LOW").toLowerCase()}`}>
      {NIVEAU(risk)}
    </span>
  );
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
  const [cascade, setCascade] = useState(null);
  const [plan, setPlan] = useState(null);
  const [chat, setChat] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [missions, setMissions] = useState([]);
  const [flotte, setFlotte] = useState([]);
  const [appels, setAppels] = useState([]);
  const [flux, setFlux] = useState(null);
  const [comparateur, setComparateur] = useState(null);
  const chatLog = useRef(null);
  const appelsVus = useRef(new Set());
  const premierBalayage = useRef(true);

  // double bip court (standard d'urgence) via WebAudio — aucun fichier
  const bipAppel = () => {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      const ctx = new Ctx();
      for (const decalage of [0, 0.18]) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.value = 880;
        const t0 = ctx.currentTime + decalage;
        gain.gain.setValueAtTime(0.001, t0);
        gain.gain.exponentialRampToValueAtTime(0.12, t0 + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.001, t0 + 0.14);
        osc.connect(gain).connect(ctx.destination);
        osc.start(t0);
        osc.stop(t0 + 0.16);
      }
      setTimeout(() => ctx.close(), 700);
    } catch {
      /* audio indisponible : silencieux */
    }
  };

  const refresh = async () => {
    try {
      const [infraData, riskData, eventsData, missionsData, flotteData, appelsData, fluxData] =
        await Promise.all([
          getInfrastructure(),
          getRisk(),
          getEvents(20),
          getMissions(),
          getFleet(),
          getCalls(8),
          getStream(),
        ]);
      setInfra(infraData);
      setRisque(riskData);
      setHistorique(eventsData);
      setMissions(missionsData);
      setFlotte(flotteData);
      setAppels(appelsData);
      setFlux(fluxData);
      // appel entrant : double bip + annonce
      const nouveaux = appelsData.filter((a) => !appelsVus.current.has(a.call_id));
      for (const a of appelsData) appelsVus.current.add(a.call_id);
      if (!premierBalayage.current && nouveaux.length > 0) {
        bipAppel();
        const premier = nouveaux[0];
        setToast(
          nouveaux.length === 1
            ? `📞 Nouvel appel ${premier.kind === "SUPPLY" ? "logistique" : "médical"} — ${premier.destination_id}`
            : `📞 ${nouveaux.length} nouveaux appels`
        );
      }
      premierBalayage.current = false;
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
    if (prediction == null && fantomes.length === 0) return;
    const t = setTimeout(() => {
      setFantomes([]);
      setPrediction(null);
    }, 15000);
    return () => clearTimeout(t);
  }, [fantomes, prediction]);

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

  const missionsActives = missions.filter((m) =>
    ["EN_ROUTE", "DIVERTED", "BLOCKED"].includes(m.status)
  );

  const chargerCascade = async (id) => {
    const incident = (risque?.incident_list || []).find(
      (item) => item.target_id === id
    );
    if (!incident) {
      setCascade(null);
      setPlan(null);
      return;
    }
    try {
      setCascade(await getEventImpact(incident.event_id));
      setPlan(await getEventRecommendations(incident.event_id));
    } catch {
      setCascade(null);
      setPlan(null);
    }
  };

  const gererSelection = (node) => {
    setCible(node);
    setRisqueSelectionne(riskById[node.id] || null);
    setPrediction(null);
    setFantomes([]);
    chargerCascade(node.id);
  };

  const ouvrirRisque = (node) => {
    const infrastructure = infra.find((item) => item.id === node.id);
    if (infrastructure) setCible(infrastructure);
    setRisqueSelectionne(node);
    chargerCascade(node.id);
  };

  // Les cartes indicatrices mènent directement à l'essentiel
  const ciblerIncident = (incident) => {
    const infraNode = infra.find((item) => item.id === incident.target_id);
    if (infraNode) setCible(infraNode);
    setRisqueSelectionne(riskById[incident.target_id] || null);
    if (!riskById[incident.target_id]) setCascade(null);
    chargerCascade(incident.target_id);
  };

  const allerVers = (idCible) => {
    const el = document.getElementById(idCible);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    el.classList.remove("zapper");
    void el.offsetWidth; // relance l'animation
    el.classList.add("zapper");
    setTimeout(() => el.classList.remove("zapper"), 1600);
  };

  const kpiVoirIncidents = () => {
    allerVers("section-incidents");
    if (kpis.actifs === 0) setToast("Aucun incident actif — la ville est calme.");
  };

  const kpiVoirRisques = () => {
    const pivot = nodesAtRisk.find((n) => n.risk === "CRITICAL") || nodesAtRisk[0];
    if (pivot) {
      ouvrirRisque(pivot);
      allerVers("panneau-focus");
    } else {
      allerVers("section-priorites");
      setToast("Aucun risque calculé actuellement.");
    }
  };

  const kpiVoirHopitaux = () => {
    const hopital = nodesAtRisk.find(
      (n) => n.kind === "Hospital" && ["HIGH", "CRITICAL"].includes(n.risk)
    );
    if (hopital) {
      ouvrirRisque(hopital);
      allerVers("panneau-focus");
    } else {
      setToast("Aucun hôpital menacé pour l'instant.");
    }
  };

  const kpiVoirProfondeur = () => {
    const incident = [...(risque?.incident_list || [])].sort(
      (a, b) => (b.max_depth || 0) - (a.max_depth || 0)
    )[0];
    if (!incident) {
      setToast("Aucune propagation en cours.");
      return;
    }
    ciblerIncident(incident);
    if (riskById[incident.target_id]) {
      allerVers("panneau-focus");
    } else {
      // la cible n'a pas de score de risque : on pointe sa carte d'incident
      allerVers(`incident-${incident.target_id}`);
    }
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
        setToast(`🔮 Simulation : ${predict.total_count} impact(s) prédit(s)`);
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

  const envoyerChat = async (question) => {
    const q = (question || chatInput).trim();
    if (!q || chatBusy) return;

    const suivants = [...chat, { role: "user", text: q }];
    setChat(suivants);
    setChatInput("");
    setChatBusy(true);

    try {
      if (q.toLowerCase() === "briefing") {
        const r = await aiBriefing();
        setChat([...suivants, { role: "ai", text: r.text, mode: r.mode }]);
      } else {
        const r = await aiAsk(q);
        setChat([...suivants, { role: "ai", text: r.answer, mode: r.mode }]);
      }
    } catch (exc) {
      setChat([...suivants, { role: "ai", text: `⛔ IA indisponible : ${exc.message}` }]);
    } finally {
      setChatBusy(false);
    }
  };

  useEffect(() => {
    if (chatLog.current) chatLog.current.scrollTop = chatLog.current.scrollHeight;
  }, [chat]);

  const resoudre = async (id) => {
    try {
      await resolveEvent(id);
      await refresh();
      setToast("✅ Incident résolu, état restauré");
    } catch (exc) {
      setToast(`⛔ ${exc.message}`);
    }
  };

  // ----- console dispatcher -----

  const activerCorridor = async (mission) => {
    try {
      await postCorridor(mission.mission_id, 3);
      setToast(`🚨 Corridor prioritaire activé pour ${mission.vehicle || "le convoi"}`);
      await refresh();
    } catch (exc) {
      setToast(`⛔ ${exc.message}`);
    }
  };

  const envoyerRadio = async (mission) => {
    try {
      await postRadio(
        mission.mission_id,
        "CMD",
        `Soyez prudent sur ${mission.route_names?.[0] || "votre axe"}, trafic dégradé.`
      );
      setToast(`📻 Radio transmise à ${mission.vehicle || "le convoi"}`);
      await refresh();
    } catch (exc) {
      setToast(`⛔ ${exc.message}`);
    }
  };

  const comparerItineraires = async (mission) => {
    if (!mission.origin_id) {
      setToast("⛔ Ancienne mission : comparateur indisponible");
      return;
    }
    try {
      const offre = await postRouteOptions(mission.origin_id, mission.destination_id, mission.profile);
      setComparateur({ missionId: mission.mission_id, ...offre });
    } catch (exc) {
      setToast(`⛔ ${exc.message}`);
    }
  };

  const imposerVariante = async (missionId, variant) => {
    try {
      await postChooseRoute(missionId, variant);
      setToast(`🧑‍✈️ Variante ${variant} imposée au véhicule`);
      setComparateur(null);
      await refresh();
    } catch (exc) {
      setToast(`⛔ ${exc.message}`);
    }
  };

  const annuler = async (missionId) => {
    try {
      await cancelMission(missionId);
      setToast("✕ Mission annulée, véhicule relâché");
      await refresh();
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
          <small>ÉTAT DE LA VILLE</small>
          <strong>● {ETATS_VILLE_FR[cityStatus] || cityStatus}</strong>
        </div>

        <div className="horloge">
          Grand Tunis
          <b>{horloge}</b>
        </div>
      </header>

      <section className="kpi-strip">
        <div
          className="kpi-horizontal kpi-rouge"
          role="button"
          tabIndex={0}
          onClick={kpiVoirIncidents}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && kpiVoirIncidents()}
          title="Ouvrir les incidents actifs"
        >
          <span>Incidents actifs</span><strong>{kpis.actifs}</strong>
        </div>
        <div
          className="kpi-horizontal kpi-ambre"
          role="button"
          tabIndex={0}
          onClick={kpiVoirRisques}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && kpiVoirRisques()}
          title="Ouvrir le risque n°1"
        >
          <span>Risques ÉLEVÉ / CRITIQUE</span><strong>{kpis.critiques}</strong>
        </div>
        <div
          className="kpi-horizontal kpi-violet"
          role="button"
          tabIndex={0}
          onClick={kpiVoirHopitaux}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && kpiVoirHopitaux()}
          title="Ouvrir l'hôpital le plus menacé"
        >
          <span>Hôpitaux menacés</span><strong>{kpis.hospitals}</strong>
        </div>
        <div
          className="kpi-horizontal kpi-cyan"
          role="button"
          tabIndex={0}
          onClick={kpiVoirProfondeur}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && kpiVoirProfondeur()}
          title="Ouvrir l'incident le plus profond"
        >
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

        <section className="dispatcher-panel">
          <div className="section-titre">Poste de commandement</div>

          <div className={`flux-chip ${flux?.online ? "flux-live" : flux?.paused ? "flux-pause" : ""}`}>
            <span className="flux-dot" />
            <div className="flux-info">
              <b>
                {flux?.online
                  ? "Sources agences en direct"
                  : flux?.paused
                    ? "Flux en pause"
                    : "Sources hors ligne"}
              </b>
              <small>
                {flux?.stats
                  ? `${flux.stats.calls} appels · ${flux.stats.incidents} incidents · ${flux.stats.resolved || 0} résolus`
                  : "…"}
              </small>
            </div>
          </div>

          <div className="flotte-liste">
            {flotte.length === 0 && (
              <div className="empty-state">Flotte non encore enregistrée.</div>
            )}
            {flotte.map((v) => {
              const st = STATUT_FLOTTE[v.status] || STATUT_FLOTTE.AVAILABLE;
              return (
                <div className={`flotte-row ${st.classe}`} key={v.callsign}>
                  <span className="flotte-emoji">{EMOJI_TYPE[v.type] || "🚙"}</span>
                  <span className="flotte-nom">
                    <b>{v.callsign}</b>
                    <small>{v.type}</small>
                  </span>
                  <span className="flotte-statut">{st.label}</span>
                  <small className="flotte-mission">{v.mission_id || "—"}</small>
                </div>
              );
            })}
          </div>

          <div className="section-titre" style={{ marginTop: 10 }}>
            Standard d'urgence
          </div>
          <div className="appels-liste">
            {appels.length === 0 && (
              <div className="empty-state">Aucun appel reçu.</div>
            )}
            {appels.slice(0, 5).map((a) => (
              <div className="appel-row" key={a.call_id}>
                <b>{a.call_id}</b>
                <span>{a.kind === "SUPPLY" ? "📦 logistique" : "🚑 médical"}</span>
                <small>→ {a.destination_id}</small>
                <span className={`appel-statut s-${(a.status || "").toLowerCase()}`}>
                  {a.status === "DISPATCHED"
                    ? "✓ assigné"
                    : a.status === "NO_VEHICLE"
                      ? "✗ aucun véhicule"
                      : a.status === "PENDING"
                        ? "⏳ en attente"
                        : a.status}
                </span>
                <small>{a.assigned_vehicle || a.note || ""}</small>
              </div>
            ))}
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
              <span className="nom">MODE SIMULATION</span>
              <small>Prévoir sans modifier la ville</small>
            </span>
            <span className={`interrupteur ${modeSimulation ? "on" : ""}`} />
          </div>
        </section>

        {prediction && (
          <section className="whatif-card">
            <div className="section-titre">Projection (simulation)</div>
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


        <section className="active-incidents" id="section-incidents">
          <div className="section-titre">Incidents actifs</div>
          {(risque?.incident_list || []).length === 0 ? (
            <div className="empty-state">✓ Aucun incident actif</div>
          ) : (
            (risque?.incident_list || []).map((incident) => (
              <article
                className="incident-card card-ciblable"
                id={`incident-${incident.target_id}`}
                key={incident.event_id}
                role="button"
                tabIndex={0}
                onClick={() => ciblerIncident(incident)}
                onKeyDown={(e) =>
                  (e.key === "Enter" || e.key === " ") && ciblerIncident(incident)
                }
                title="Ouvrir cet incident"
              >
                <div className="incident-head">
                  <span className="incident-type">{ETYPES_FR[incident.type] || incident.type}</span>
                  <span>{NIVEAU(incident.severity)}</span>
                </div>
                <strong>{incident.target_id}</strong>
                <small>
                  {incident.total_count} impact(s) · profondeur {incident.max_depth}
                </small>
                <button onClick={(e) => { e.stopPropagation(); resoudre(incident.event_id); }}>Résoudre</button>
              </article>
            ))
          )}
        </section>

        <section className="missions-panel">
          <div className="section-titre">Missions en cours ({missionsActives.length})</div>
          {missionsActives.length === 0 && (
            <div className="empty-state">Aucun véhicule en mission. La flotte veille.</div>
          )}
          {missionsActives.map((m) => (
            <article className="mission-card" key={m.mission_id}>
              <div className="mission-head">
                <span className="mission-vehicule">
                  {EMOJI_VEHICULE[m.profile] || "🚑"}{" "}
                  <b>{m.vehicle || "Convoi"}</b>
                </span>
                <span className={`mission-statut ${(STATUS_MISSION[m.status] || {}).classe || ""}`}>
                  {(STATUS_MISSION[m.status] || {}).label || m.status}
                </span>
              </div>
              <div className="mission-lieu">
                {m.origin_name} → <b>{m.destination_name}</b>
              </div>
              <div className="mission-meta">
                <span><b>{m.mission_id}</b></span>
                <span>ETA <b>{m.remaining_min ?? "—"} min</b></span>
                <span>{m.route_names?.length || 0} rues</span>
                {m.corridor_active && <span className="mission-corridor">🚨 CORRIDOR</span>}
              </div>
              <div className="mission-route" title={(m.route_names || []).join(" › ")}>
                {(m.route || []).join(" › ")}
              </div>

              <div className="mission-actions">
                <button
                  className="btn-mission"
                  onClick={() => activerCorridor(m)}
                  disabled={m.corridor_active}
                  title="Perce la congestion (gyrophare)"
                >
                  🚨 Corridor
                </button>
                <button
                  className="btn-mission"
                  onClick={() => envoyerRadio(m)}
                  title="Message radio au conducteur"
                >
                  📻 Radio
                </button>
                <button
                  className="btn-mission"
                  onClick={() => comparerItineraires(m)}
                  title="3 itinéraires proposés"
                >
                  🧭 Comparateur
                </button>
                <button
                  className="btn-mission btn-annuler"
                  onClick={() => annuler(m.mission_id)}
                  title="Annuler la mission"
                >
                  ✕
                </button>
              </div>

              {comparateur?.missionId === m.mission_id && (
                <div className="comparateur">
                  <div className="section-titre">🧭 3 itinéraires possibles</div>
                  {comparateur.options.map((o) => (
                    <div className={`comparateur-row v-${o.variant.toLowerCase()}`} key={o.variant}>
                      <span className="comp-label">{o.label}</span>
                      <span className="comp-mesures">
                        {o.estimated_time_min} min · {o.distance_km} km
                      </span>
                      <small className="comp-routes">{o.route_names.join(" › ")}</small>
                      <button onClick={() => imposerVariante(m.mission_id, o.variant)}>
                        Imposer
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {m.timeline?.length > 0 && (
                <div className="mission-journal">
                  {m.timeline.slice(-2).map((entry, i) => (
                    <div className="journal-row" key={i}>
                      <small>{new Date(entry.at).toLocaleTimeString("fr-FR", { hour12: false })}</small>
                      <span>{entry.message}</span>
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}
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
          itineraires={plan?.detours || []}
          missions={missionsActives}
          options={comparateur?.options || []}
        />
        {toast && <div className="toast">{toast}</div>}
      </main>

      {chatOpen && (
        <div className="messenger">
          <div className="messenger-header">
            <div className="messenger-identite">
              <span className="messenger-avatar">🦋</span>
              <div>
                <b>Copilote IA</b>
                <small>
                  {chatBusy ? "écrit…" : "graphe + Llama 3.1 · Grand Tunis"}
                </small>
              </div>
            </div>
            <button
              className="messenger-close"
              onClick={() => setChatOpen(false)}
              title="Fermer"
            >
              ✕
            </button>
          </div>

          <div className="chat-log" ref={chatLog}>
            {chat.length === 0 ? (
              <div className="empty-state">
                Interrogez le jumeau numérique : le graphe fournit les faits, l'IA reformule.
              </div>
            ) : (
              chat.map((msg, i) => (
                <div
                  className={`chat-bubble msg-${msg.role}`}
                  key={i}
                >
                  {msg.text}
                  {msg.mode && (
                    <div className="mode-note">
                      {msg.mode === "llm" ? "graphe + Llama 3.1" : "résumé local (LLM off)"}
                    </div>
                  )}
                </div>
              ))
            )}
            {chatBusy && (
              <div className="chat-bubble msg-ai en-attente">
                <span className="point-anim" />
                <span className="point-anim" />
                <span className="point-anim" />
              </div>
            )}
          </div>

          <div className="chat-chips">
            <button onClick={() => envoyerChat("Pourquoi H1 est-il critique ?")}
              disabled={chatBusy}>Pourquoi H1 ?</button>
            <button onClick={() => envoyerChat("Que faire pour R19 ?")}
              disabled={chatBusy}>Plan R19</button>
            <button onClick={() => envoyerChat("Briefing")}
              disabled={chatBusy}>📋 Briefing</button>
          </div>

          <div className="chat-input">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") envoyerChat(); }}
              placeholder="Poser une question au jumeau numérique..."
              disabled={chatBusy}
            />
            <button onClick={() => envoyerChat()} disabled={chatBusy || !chatInput.trim()}>
              {chatBusy ? "…" : "→"}
            </button>
          </div>
        </div>
      )}

      <button
        className={`fab-copilote ${chatOpen ? "ouvert" : ""}`}
        onClick={() => setChatOpen((o) => !o)}
        title="Copilote IA"
      >
        {chatOpen ? "✕" : "🦋"}
      </button>

      <aside className="risk-center">
        <div className="risk-center-header">
          <div>
            <small>ANALYSE EN DIRECT</small>
            <h2>Centre de risques</h2>
          </div>
          <span>{nodesAtRisk.length} nœuds</span>
        </div>

        {risqueSelectionne ? (
          <section className="risk-focus" id="panneau-focus">
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
            {cascade && (
              <>
                <div className="section-titre" style={{ marginTop: 10 }}>
                  Ce qu'il impacte ({cascade.total_count})
                </div>
                {cascade.impacts.length === 0 ? (
                  <div className="empty-state">Aucune propagation détectée.</div>
                ) : (
                  <div className="prediction-list">
                    {cascade.impacts.slice(0, 8).map((impact) => (
                      <div className="prediction-row" key={impact.id}>
                        <span>
                          {EMOJI_KIND[impact.kind] || "📍"} {impact.name}
                          <small> · niveau {impact.depth}</small>
                        </span>
                        <RiskBadge risk={impact.risk} />
                        <b>{impact.score}</b>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
            {plan && (
              <section className="action-plan">
                <div className="section-titre" style={{ marginTop: 10 }}>
                  📞 Plan d'action
                </div>
                <div className="plan-contacts">
                  {plan.contacts.map((contact) => (
                    <span className="plan-contact" key={contact}>📞 {contact}</span>
                  ))}
                </div>
                <ul className="plan-actions">
                  {plan.actions.map((action) => (
                    <li key={action}>▸ {action}</li>
                  ))}
                </ul>
                {(plan.alternatives || []).length > 0 && (
                  <>
                    <div className="section-titre">Alternatives de secours</div>
                    {plan.alternatives.map((alt) => (
                      <div className="plan-alt" key={alt.id}>
                        <b>{alt.id}</b> {alt.name}
                        <small>{alt.note}</small>
                      </div>
                    ))}
                  </>
                )}
                {(plan.detours || []).length > 0 && (
                  <>
                    <div className="section-titre">Itinéraires alternatifs (cyan)</div>
                    {plan.detours.map((detour) => (
                      <div className="plan-alt" key={detour.dest_id}>
                        <b>→ {detour.dest_id}</b> {detour.dest_name}
                        <small>
                          via {detour.via_names.join(" › ")} ({detour.jumps} saut(s))
                        </small>
                      </div>
                    ))}
                  </>
                )}
              </section>
            )}
          </section>
        ) : (
          <div className="risk-hint" id="panneau-focus">
            Sélectionnez un risque ci-dessous pour afficher son explication.
          </div>
        )}

        <section className="risk-list-wrap" id="section-priorites">
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
              <b>{ETYPES_FR[ev.type] || ev.type}</b>
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
        <span className="footer-right">Urban Butterfly · Jumeau numérique NoSQL</span>
      </footer>
    </div>
  );
}
