import { useEffect, useMemo, useRef, useState } from "react";
import MapView from "./components/MapView.jsx";
import ReplayView from "./components/ReplayView.jsx";
import InfrastructureSearch from "./components/InfrastructureSearch.jsx";
import { recordIncoming } from "./notificationSound.js";
import { prioritizeNotifications } from "./notificationPriority.js";
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
  getInterventionPreview,
  getDecisionRanking,
  getAudit,
  getNotifications,
  acknowledgeNotification,
  getEventImpact,
  getEventRecommendations,
  postEvent,
  postWhatif,
  resolveEvent,
  getMissions,
  getFleet,
  getCalls,
  getStream,
  postStreamAction,
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
  RESERVED: { label: "RÉSERVÉ", classe: "f-mission" },
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

function AccesIntervention({ access }) {
  if (access?.status === "REACHABLE") {
    return <span>🚙 Accès estimé : {access.minutes} min depuis {access.base_id} ({access.vehicle})</span>;
  }
  if (access?.status === "NO_VEHICLE") return <span>⚠ Aucun véhicule disponible actuellement</span>;
  return <span>⚠ Aucun accès routier calculable depuis la flotte disponible</span>;
}

function ScenarioCompare({ scenario }) {
  return (
    <div className="decision-comparison-card">
      <b>{ETYPES_FR[scenario.event_type] || scenario.event_type} · {scenario.target_id}</b>
      <strong>{scenario.hospital_points} points estimés pour les hôpitaux</strong>
      <span>{scenario.hospital_count} hôpital(s) · {scenario.changed_count} nœud(s) amélioré(s)</span>
      <span>{scenario.total_points} points de réduction cumulés (non additionnés au score global)</span>
      <AccesIntervention access={scenario.access} />
      <small>{scenario.nodes.filter((n) => n.reduction > 0).slice(0, 3).map((n) =>
        `${n.name} ${n.before} → ${n.after}`).join(" · ") || "Aucune baisse estimée"}</small>
    </div>
  );
}

export default function App({ readonly = false, secured = false }) {
  const [infra, setInfra] = useState([]);
  const [risque, setRisque] = useState(null);
  const [cible, setCible] = useState(null);
  const [searchFocus, setSearchFocus] = useState(null);
  const [modeSimulation, setModeSimulation] = useState(false);
  const [vagues, setVagues] = useState([]);
  const [fantomes, setFantomes] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [selectedWhatifImpactId, setSelectedWhatifImpactId] = useState(null);
  const [toast, setToast] = useState(null);
  const [horloge, setHorloge] = useState("");
  const [erreur, setErreur] = useState(null);
  const [risqueSelectionne, setRisqueSelectionne] = useState(null);
  const [cascade, setCascade] = useState(null);
  const [plan, setPlan] = useState(null);
  const [sourceEventId, setSourceEventId] = useState(null);
  const analyseRequest = useRef(0);
  const [projection, setProjection] = useState(null);
  const [projectionBusy, setProjectionBusy] = useState(false);
  const projectionRequest = useRef(0);
  const [decisions, setDecisions] = useState(null);
  const [decisionsBusy, setDecisionsBusy] = useState(false);
  const [scenarioId, setScenarioId] = useState(null);
  const [compareId, setCompareId] = useState(null);
  const [audit, setAudit] = useState([]);
  const [replayOpen, setReplayOpen] = useState(false);
  const [notificationFilter, setNotificationFilter] = useState("NEW");
  const [notificationInbox, setNotificationInbox] = useState({ items: [], counts: {} });
  const [notificationError, setNotificationError] = useState(null);
  const [ackBusy, setAckBusy] = useState(null);
  const [notificationFocus, setNotificationFocus] = useState(null);
  const notificationAnalysisRequest = useRef(0);
  const [notificationImpact, setNotificationImpact] = useState(null);
  const [notificationImpactError, setNotificationImpactError] = useState(null);
  const [missions, setMissions] = useState([]);
  const [flotte, setFlotte] = useState([]);
  const [appels, setAppels] = useState([]);
  const [flux, setFlux] = useState(null);
  const [controlBusy, setControlBusy] = useState(false);
  const [comparateur, setComparateur] = useState(null);
  const soundLedgerFallback = useRef(new Map());

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
      const [infraData, riskData, missionsData, flotteData, appelsData, fluxData] =
        await Promise.all([
          getInfrastructure(),
          getRisk(),
          getMissions(),
          getFleet(),
          getCalls(8),
          getStream(),
        ]);
      setInfra(infraData);
      setRisque(riskData);
      setMissions(missionsData);
      setFlotte(flotteData);
      setAppels(appelsData);
      setFlux(fluxData);
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

  const piloterSimulation = async () => {
    if (controlBusy || readonly || !flux) return;
    const action = flux.online ? "stop" : "start";
    setControlBusy(true);
    try {
      setFlux(await postStreamAction(action));
      setToast(action === "start" ? "▶ Simulation démarrée par vous" : "■ Simulation arrêtée");
      await refresh();
    } catch (exc) {
      setToast(`⛔ Commande impossible : ${exc.message}`);
    } finally {
      setControlBusy(false);
    }
  };

  useEffect(() => {
    if (!secured || readonly) return;
    const charger = () => getAudit().then(setAudit).catch(() => {});
    charger();
    const timer = setInterval(charger, 30000);
    return () => clearInterval(timer);
  }, [secured, readonly]);

  useEffect(() => {
    let active = true;
    const charger = async () => {
      try {
        const nouvelles = await getNotifications("NEW");
        if (!active) return;
        const storage = {
          getItem: (key) => {
            try { return window.localStorage.getItem(key) ?? soundLedgerFallback.current.get(key) ?? null; }
            catch { return soundLedgerFallback.current.get(key) ?? null; }
          },
          setItem: (key, value) => {
            soundLedgerFallback.current.set(key, value);
            try { window.localStorage.setItem(key, value); } catch { /* stockage désactivé */ }
          },
        };
        const signaler = () => {
          if (!active) return;
          const incoming = recordIncoming(storage, nouvelles.items);
          if (incoming.length) {
            bipAppel();
            setToast(incoming.length === 1
              ? `🔔 Nouvelle alerte : ${incoming[0].title} — ${incoming[0].location_id}`
              : `🔔 ${incoming.length} nouvelles alertes`);
          }
        };
        if (navigator.locks?.request) await navigator.locks.request("urban-butterfly-notification-sound", signaler);
        else signaler();
        const result = notificationFilter === "NEW" ? nouvelles : await getNotifications(notificationFilter);
        if (active) { setNotificationInbox(result); setNotificationError(null); }
      } catch (exc) { if (active) setNotificationError(exc.message); }
    };
    charger();
    const timer = setInterval(charger, 6000);
    return () => { active = false; clearInterval(timer); };
  }, [notificationFilter]);

  const accuserNotification = async (id) => {
    setAckBusy(id);
    try {
      await acknowledgeNotification(id);
      setNotificationInbox(await getNotifications(notificationFilter));
    } catch (exc) {
      setNotificationError(exc.message);
    } finally {
      setAckBusy(null);
    }
  };

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
    }, 60000);
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

  const rankedNotifications = useMemo(
    () => prioritizeNotifications(notificationInbox.items, infra, nodesAtRisk),
    [notificationInbox.items, infra, nodesAtRisk]
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

  const risqueAffiche = risqueSelectionne ? riskById[risqueSelectionne.id] || null : null;
  const sourceActive = risqueAffiche?.sources?.find((source) => source.event_id === sourceEventId)
    || risqueAffiche?.sources?.[0];
  const selectedWhatifImpact = prediction?.impacts.find((impact) => impact.id === selectedWhatifImpactId) || null;
  const classementObsolete = decisions && (
    decisions.scenarios.length !== (risque?.incident_list || []).length ||
    decisions.scenarios.some((s) => !(risque?.incident_list || []).some((i) => i.event_id === s.event_id))
  );
  const scenarioA = decisions?.scenarios.find((s) => s.event_id === scenarioId);
  const scenarioB = decisions?.scenarios.find((s) => s.event_id === compareId);

  const chargerDecisions = async () => {
    setDecisionsBusy(true);
    try {
      const resultat = await getDecisionRanking();
      setDecisions({ ...resultat, calculated_at: new Date().toLocaleTimeString("fr-FR") });
      setScenarioId(resultat.scenarios[0]?.event_id || null);
      setCompareId(null);
    } catch (exc) {
      setToast(`Classement indisponible : ${exc.message}`);
    } finally {
      setDecisionsBusy(false);
    }
  };

  const chargerCascade = async (eventId) => {
    const demande = ++analyseRequest.current;
    setCascade(null);
    setPlan(null);
    if (!eventId) return;
    try {
      const [impact, recommandations] = await Promise.all([
        getEventImpact(eventId), getEventRecommendations(eventId),
      ]);
      if (demande !== analyseRequest.current) return;
      setCascade(impact);
      setPlan(recommandations);
    } catch {
      if (demande !== analyseRequest.current) return;
      setCascade(null);
      setPlan(null);
    }
  };

  const choisirSource = (eventId) => {
    projectionRequest.current += 1;
    setProjection(null);
    setProjectionBusy(false);
    setSourceEventId(eventId);
    chargerCascade(eventId);
  };

  const estimerResolution = async (eventId) => {
    const demande = ++projectionRequest.current;
    setProjection(null);
    setProjectionBusy(true);
    try {
      const resultat = await getInterventionPreview(eventId);
      if (demande !== projectionRequest.current) return;
      setProjection({ ...resultat, calculated_at: new Date().toLocaleTimeString("fr-FR") });
    } catch (exc) {
      if (demande === projectionRequest.current) setToast(`Simulation impossible : ${exc.message}`);
    } finally {
      if (demande === projectionRequest.current) setProjectionBusy(false);
    }
  };

  const gererSelection = (node) => {
    setSelectedWhatifImpactId(null);
    setSearchFocus(null);
    notificationAnalysisRequest.current += 1;
    setNotificationImpact(null);
    setNotificationImpactError(null);
    setNotificationFocus(null);
    setCible(node);
    const selection = riskById[node.id] || null;
    setRisqueSelectionne(selection);
    setPrediction(null);
    setFantomes([]);
    choisirSource(selection?.sources?.[0]?.event_id);
  };

  const choisirLieuRecherche = (node) => {
    gererSelection(node);
    setSearchFocus({ id: node.id, key: Date.now() });
    document.getElementById("carte")?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const ouvrirRisque = (node) => {
    fermerNotification();
    const infrastructure = infra.find((item) => item.id === node.id);
    if (infrastructure) setCible(infrastructure);
    setRisqueSelectionne(node);
    choisirSource(node.sources?.[0]?.event_id);
  };

  // Les cartes indicatrices mènent directement à l'essentiel
  const ciblerIncident = (incident) => {
    fermerNotification();
    const infraNode = infra.find((item) => item.id === incident.target_id);
    if (infraNode) setCible(infraNode);
    const selection = riskById[incident.target_id] || null;
    setRisqueSelectionne(selection);
    choisirSource(selection?.sources?.find((s) => s.event_id === incident.event_id)?.event_id
      || selection?.sources?.[0]?.event_id);
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

  const ouvrirNotification = (item) => {
    const node = infra.find((entry) => entry.id === item.location_id);
    if (!node || node.lat == null || node.lon == null) {
      setToast(`Lieu ${item.location_id} introuvable sur la carte actuelle.`);
      return;
    }
    const demande = ++notificationAnalysisRequest.current;
    setNotificationImpact(null);
    setNotificationImpactError(null);
    setCible(node);
    const selection = riskById[node.id] || null;
    setRisqueSelectionne(selection);
    const eventId = item.category === "INCIDENT" && item.source_key?.startsWith("event:")
      ? item.source_key.slice(6) : null;
    choisirSource(eventId
      ? selection?.sources?.find((source) => source.event_id === eventId)?.event_id
      : selection?.sources?.[0]?.event_id);
    setNotificationFocus({ ...item, focusKey: `${item.id}:${Date.now()}` });
    document.getElementById("carte")?.scrollIntoView({ behavior: "smooth", block: "center" });
    if (eventId && item.state !== "RESOLVED") {
      getEventImpact(eventId).then((impact) => {
        if (demande === notificationAnalysisRequest.current) setNotificationImpact(impact);
      }).catch(() => {
        if (demande === notificationAnalysisRequest.current) {
          setNotificationImpactError("Estimation temporairement indisponible.");
        }
      });
    }
  };

  const fermerNotification = () => {
    notificationAnalysisRequest.current += 1;
    setNotificationFocus(null);
    setNotificationImpact(null);
    setNotificationImpactError(null);
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
        setSelectedWhatifImpactId(null);
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
        setSelectedWhatifImpactId(null);
        setToast(`Incident propagé : ${resultat.impact.total_count} impact(s)`);
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

  if (replayOpen) return <ReplayView infrastructure={infra} onClose={() => {
    setReplayOpen(false);
    refresh();
  }} />;

  return (
    <div className="app app-v2">
      <header className="header">
        <div className="titre">
          <h1>Vigie <span>Urbaine</span></h1>
          <p>Centre d'analyse des risques urbains en cascade</p>
        </div>
        <button className="replay-entry" onClick={() => setReplayOpen(true)}>
          ◷ Relecture de crise
        </button>
        <button className="notification-entry" onClick={() => {
          setNotificationFilter("NEW");
          document.getElementById("section-notifications")?.scrollIntoView({ behavior: "smooth", block: "start" });
        }} aria-label={`${notificationInbox.counts.NEW || 0} notifications à traiter`}>
          🔔 {notificationInbox.counts.NEW || 0} à traiter
        </button>

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
                  ? "Simulation en cours"
                  : flux?.paused
                    ? "Flux en pause"
                    : "Simulateur arrêté"}
              </b>
              <small>
                {flux?.stats
                  ? `${flux.stats.calls} appels · ${flux.stats.incidents} incidents · ${flux.stats.resolved || 0} résolus`
                  : "…"}
              </small>
            </div>
          </div>

          <div className="simulation-control">
            <button type="button" onClick={piloterSimulation} disabled={readonly || controlBusy || !flux}
              className={flux?.online ? "simulation-stop" : "simulation-start"}>
              {controlBusy ? "Commande en cours…" : flux?.online ? "■ Arrêter le simulateur" : "▶ Démarrer le simulateur"}
            </button>
            <small>{readonly ? "Lecture seule : commande réservée à l'opérateur." : flux?.online
              ? "Appels, incidents et météo alimentent la simulation."
              : "Rien ne démarre automatiquement. Les premiers appels arrivent après 35 à 90 s."}</small>
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
                        : a.status === "ROUTE_UNAVAILABLE"
                          ? "⛔ accès routier indisponible"
                        : a.status === "PENDING"
                          ? "⏳ attente véhicule"
                        : a.status}
                </span>
                <small>{a.assigned_vehicle || a.queue_reason || a.note || ""}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="notification-panel" id="section-notifications">
          <div className="section-titre">Centre de notifications</div>
          <p>Alertes conservées en base · actualisation toutes les 6 secondes. Les nouvelles urgences sont signalées une fois par navigateur ; le premier chargement reste silencieux.</p>
          <p className="priority-method">À traiter : ordre calculé selon gravité enregistrée, ancienneté et hôpitaux concernés (directement ou estimés par le modèle). P1/P2/P3 ne sont ni une nouvelle gravité constatée ni un ordre d'intervention.</p>
          <div className="notification-filters" role="group" aria-label="État des notifications">
            {[
              ["NEW", "À traiter"], ["ACKNOWLEDGED", "Pris en compte"], ["RESOLVED", "Résolus"],
            ].map(([state, label]) => (
              <button key={state} className={notificationFilter === state ? "actif" : ""}
                onClick={() => setNotificationFilter(state)} aria-pressed={notificationFilter === state}>
                {label} · {notificationInbox.counts[state] || 0}
              </button>
            ))}
          </div>
          {notificationError && <div className="notification-error" role="alert">Notifications indisponibles : {notificationError}</div>}
          {notificationInbox.items.length === 0 && !notificationError && (
            <div className="empty-state">Aucune notification dans cette catégorie.</div>
          )}
          {(notificationInbox.counts[notificationFilter] || 0) > notificationInbox.items.length && (
            <small className="priority-limit">Classement limité aux {notificationInbox.items.length} notifications chargées ; {notificationInbox.counts[notificationFilter]} au total.</small>
          )}
          <div className="notification-list">
            {rankedNotifications.map((item) => (
              <article className={`notification-card n-${item.severity.toLowerCase()}`} key={item.id}>
                <div className="notification-heading">
                  <b>{item.category === "INCIDENT" ? "⚠ Incident" : item.category === "CALL" ? "☎ Appel" : "🚙 Mission"}</b>
                  <span>{NIVEAU(item.severity)}</span>
                </div>
                {item.priority && (
                  <div className={`notification-priority priority-${item.priority.level.toLowerCase()}`}>
                    <b>{item.priority.level} · Priorité calculée</b>
                    <small>{item.priority.reasons.join(" · ")}</small>
                  </div>
                )}
                <strong>{item.title} · {item.location_id}</strong>
                <p>{item.detail}</p>
                <small>{item.producer} · {new Date(item.created_at).toLocaleString("fr-FR")}</small>
                <button onClick={() => ouvrirNotification(item)}>
                  Voir le lieu sur la carte
                </button>
                {item.state === "NEW" && !readonly && (
                  <button disabled={ackBusy === item.id} onClick={() => accuserNotification(item.id)}>
                    {ackBusy === item.id ? "Enregistrement…" : "Prendre en compte"}
                  </button>
                )}
                {item.acknowledged_by && <small>Pris en compte par {item.acknowledged_by}</small>}
              </article>
            ))}
          </div>
        </section>

        <section>
          <div className="section-titre">Déclencher un incident</div>
          {readonly && <small>Lecture seule : résolution et déclenchement réservés à l'opérateur.</small>}
          <div className="boutons-incident">
            {TYPES_INCIDENT.map((d) => (
              <button
                key={d.type}
                className={`btn ${d.classe}`}
                disabled={readonly || (!modeSimulation && !flux?.online) || !cible || !d.cibles.includes(cible.kind)}
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
              setSelectedWhatifImpactId(null);
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
            <button className="whatif-clear" onClick={() => { setPrediction(null); setFantomes([]); setSelectedWhatifImpactId(null); }}>Effacer la projection</button>
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
            <div className="prediction-list" aria-label="Sites estimés touchés">
              {prediction.impacts.map((impact) => (
                <button type="button" className="prediction-row" key={impact.id}
                  onClick={() => {
                    setSelectedWhatifImpactId(impact.id);
                    document.getElementById("carte")?.scrollIntoView({ behavior: "smooth", block: "center" });
                  }}>
                  <span>{EMOJI_KIND[impact.kind] || "📍"} {impact.name}</span>
                  <RiskBadge risk={impact.risk} />
                  <b>{impact.score}</b>
                </button>
              ))}
            </div>
            <small>Cliquez sur un site de la liste ou son cercle sur la carte pour expliquer l'impact estimé.</small>
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
                  {incident.total_count} site(s) potentiellement touché(s) · profondeur estimée {incident.max_depth}
                </small>
                {!readonly && <button onClick={(e) => { e.stopPropagation(); resoudre(incident.event_id); }}>Résoudre</button>}
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
                  disabled={readonly || m.corridor_active}
                  title="Perce la congestion (gyrophare)"
                >
                  🚨 Corridor
                </button>
                <button
                  className="btn-mission"
                  onClick={() => envoyerRadio(m)}
                  disabled={readonly}
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
                  disabled={readonly}
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
                      <button disabled={readonly} onClick={() => imposerVariante(m.mission_id, o.variant)}>
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
        {secured && !readonly && (
          <section className="audit-panel">
            <div className="section-titre">Journal des accès et décisions</div>
            <small>Actions HTTP enregistrées, y compris refus d'accès. Les corps de requête ne sont pas conservés.</small>
            {audit.length === 0 && <div className="empty-state">Aucune action enregistrée.</div>}
            {audit.map((entry, index) => (
              <div className="audit-entry" key={`${entry.at}-${index}`}>
                <b>{entry.actor} · {entry.method} {entry.path}</b>
                <span>{entry.status} · {new Date(entry.at).toLocaleString("fr-FR")}</span>
              </div>
            ))}
          </section>
        )}
      </aside>

      <main className="map-zone">
        <InfrastructureSearch infrastructure={infra} onChoose={choisirLieuRecherche} />
        <MapView
          infra={infra}
          cibleId={cible?.id}
          searchFocus={searchFocus}
          onSelection={gererSelection}
          onWhatifImpactSelection={(impact) => setSelectedWhatifImpactId(impact.id)}
          selectedWhatifImpact={selectedWhatifImpact}
          onCloseWhatifImpact={() => setSelectedWhatifImpactId(null)}
          vaguesCascades={vagues}
          fantomes={fantomes}
          riskById={riskById}
          chaineRisque={sourceActive?.chain || []}
          sourceRisqueId={sourceActive?.event_id}
          itineraires={plan?.detours || []}
          missions={missionsActives}
          options={comparateur?.options || []}
          notificationFocus={notificationFocus}
          notificationImpact={notificationImpact}
          notificationImpactError={notificationImpactError}
          whatifImpact={prediction}
          liveRiskImpacts={nodesAtRisk}
          onCloseNotification={fermerNotification}
        />
        {toast && <div className="toast">{toast}</div>}
      </main>

      <aside className="risk-center">
        <div className="risk-center-header">
          <div>
            <small>ANALYSE EN DIRECT</small>
            <h2>Centre de risques</h2>
          </div>
          <span>{nodesAtRisk.length} nœuds</span>
        </div>

        <section className="decision-panel">
          <div className="section-titre">Priorités d'intervention estimées</div>
          <p>Classement analytique : bénéfice potentiel pour les hôpitaux, puis réduction totale des scores. Ce n'est pas un ordre opérationnel.</p>
          <button className="risk-preview-button" onClick={chargerDecisions} disabled={decisionsBusy}>
            {decisionsBusy ? "Calcul des scénarios…" : "Comparer les résolutions possibles"}
          </button>
          {decisions && (
            <>
              <small>Situation à {decisions.calculated_at} · scénarios indépendants · aucune intervention effectuée</small>
              {classementObsolete && <div className="decision-obsolete">La situation a changé : relancez le calcul avant de décider.</div>}
              {decisions.scenarios.length === 0 ? (
                <div className="empty-state">Aucun incident actif à comparer.</div>
              ) : (
                <>
                  <div className="decision-list">
                    {decisions.scenarios.map((s, i) => (
                      <button
                        key={s.event_id}
                        className={`decision-row ${scenarioId === s.event_id ? "actif" : ""}`}
                        onClick={() => {
                          setScenarioId(s.event_id);
                          if (compareId === s.event_id) setCompareId(null);
                        }}
                        aria-pressed={scenarioId === s.event_id}
                      >
                        <b>#{i + 1} {ETYPES_FR[s.event_type] || s.event_type} · {s.target_id}</b>
                        <span>{s.hospital_points} points hôpitaux · {s.changed_count} lieux améliorés</span>
                        <AccesIntervention access={s.access} />
                      </button>
                    ))}
                  </div>
                  {scenarioA && (
                    <div className="decision-comparison">
                      <div className="section-titre">Comparer deux interventions</div>
                      <label htmlFor="second-scenario">Seconde intervention (comparaison indépendante)</label>
                      <select
                        id="second-scenario"
                        value={compareId || ""}
                        onChange={(e) => setCompareId(e.target.value || null)}
                      >
                        <option value="">Choisir un autre incident…</option>
                        {decisions.scenarios.filter((s) => s.event_id !== scenarioId).map((s) => (
                          <option key={s.event_id} value={s.event_id}>
                            {ETYPES_FR[s.event_type] || s.event_type} · {s.target_id}
                          </option>
                        ))}
                      </select>
                      <ScenarioCompare scenario={scenarioA} />
                      {scenarioB && scenarioB.event_id !== scenarioA.event_id && <ScenarioCompare scenario={scenarioB} />}
                      <small>Temps d'accès = trajet estimé depuis une base de véhicule disponible, avec blocages et trafic actuels. N'inclut ni mobilisation, ni réparation. Les bénéfices de deux interventions ne s'additionnent pas.</small>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </section>

        {risqueAffiche ? (
          <section className="risk-focus" id="panneau-focus">
            <div className="risk-focus-top">
              <div className="risk-score-large">{sourceActive?.score ?? risqueAffiche.score}</div>
              <div>
                <RiskBadge risk={sourceActive ? (sourceActive.score >= 70 ? "CRITICAL" : sourceActive.score >= 50 ? "HIGH" : sourceActive.score >= 30 ? "MEDIUM" : "LOW") : risqueAffiche.risk} />
                <h3>{risqueAffiche.name}</h3>
                <small>{NATURES_FR[risqueAffiche.kind] || risqueAffiche.kind} · {risqueAffiche.id}</small>
              </div>
            </div>
            <div className="risk-meter">
              <i style={{ width: `${sourceActive?.score ?? risqueAffiche.score}%` }} />
            </div>
            <p className="risk-method">Score estimé par incident, de 0 à 100. Le risque global retient le score le plus élevé, sans additionner les incidents.</p>
            <div className="section-titre">Incidents contributeurs ({risqueAffiche.sources?.length || 0})</div>
            <div className="risk-sources">
              {(risqueAffiche.sources || []).map((source) => (
                <button
                  key={source.event_id}
                  className={`risk-source ${source.event_id === sourceActive?.event_id ? "actif" : ""}`}
                  onClick={() => choisirSource(source.event_id)}
                  aria-pressed={source.event_id === sourceActive?.event_id}
                >
                  <span>{ETYPES_FR[source.type] || source.type} · {source.target_id}</span>
                  <b>{source.score}/100</b>
                </button>
              ))}
            </div>
            {sourceActive && (
              <div className="risk-cause">
                <div className="risk-cause-observe">Incident enregistré dans la simulation · {ETYPES_FR[sourceActive.type] || sourceActive.type} sur {sourceActive.target_id} · intensité {NIVEAU(sourceActive.severity)}</div>
                <div className="risk-cause-model">Dépendances estimées par le graphe · {sourceActive.depth} {sourceActive.depth > 1 ? "liens" : "lien"} · tracé schématique, pas un trajet routier</div>
                <ol className="risk-chain">
                  {sourceActive.chain.map((etape, index) => (
                    <li key={`${etape.id}-${index}`}>
                      <span>{index === 0 ? "ORIGINE" : index === sourceActive.chain.length - 1 ? "CONSÉQUENCE" : `ÉTAPE ${index}`}</span>
                      <b>{etape.name || etape.id}</b>
                      <small>{NATURES_FR[etape.kind] || "Infrastructure"} · {etape.id}</small>
                    </li>
                  ))}
                </ol>
              </div>
            )}
            {sourceActive && (
              <div className="risk-projection">
                <div className="section-titre">Effet d'une intervention</div>
                <button
                  className="risk-preview-button"
                  onClick={() => estimerResolution(sourceActive.event_id)}
                  disabled={projectionBusy}
                >
                  {projectionBusy ? "Calcul en cours…" : "Estimer la résolution de cet incident"}
                </button>
                {projection?.event_id === sourceActive.event_id && (
                  <div className="risk-preview-result" aria-live="polite">
                    <p>Scénario hypothétique · {projection.calculated_at} · aucun incident réellement résolu</p>
                    {(() => {
                      const ici = projection.nodes.find((n) => n.id === risqueAffiche.id);
                      return ici && (
                        <div className="risk-preview-score">
                          <span>Risque global de {risqueAffiche.name}</span>
                          <strong>{ici.before} → {ici.after}/100</strong>
                          <small>{ici.reduction > 0 ? `−${ici.reduction} points estimés` : "Aucun changement estimé : d'autres incidents maintiennent le risque."}</small>
                        </div>
                      );
                    })()}
                    <div className="risk-preview-totals">
                      <span>{projection.changed_count} nœud(s) à risque réduit</span>
                      <span>{projection.no_longer_exposed} nœud(s) sans exposition restante</span>
                      <span>{projection.incidents_before} → {projection.incidents_after} incidents</span>
                    </div>
                    {projection.nodes.some((n) => n.reduction > 0) && (
                      <div className="risk-preview-list">
                        <b>Principales diminutions estimées</b>
                        {projection.nodes.filter((n) => n.reduction > 0).slice(0, 5).map((n) => (
                          <div key={n.id}>
                            <span>{NATURES_FR[n.kind] || "Infrastructure"} · {n.name}</span>
                            <strong>{n.before} → {n.after}</strong>
                          </div>
                        ))}
                      </div>
                    )}
                    <small>{projection.note} La situation peut évoluer : relancez le calcul pour l'actualiser.</small>
                  </div>
                )}
              </div>
            )}
            <div className="section-titre">Pourquoi ce risque ?</div>
            <ul className="risk-reasons">
              {(sourceActive?.reasons || risqueAffiche.reasons || []).map((reason, i) => (
                <li key={i}>{reason}</li>
              ))}
            </ul>
            {cascade?.event_id === sourceActive?.event_id && (
              <>
                <div className="section-titre" style={{ marginTop: 10 }}>
                  Impacts estimés de cet incident ({cascade.total_count})
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
            {plan && cascade?.event_id === sourceActive?.event_id && (
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

      </aside>

      {erreur && <div className="connection-banner" role="alert">
        <b>Connexion interrompue</b><span>{erreur}</span>
      </div>}
    </div>
  );
}
