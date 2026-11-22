import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { NATURES_FR, PROFILS_FR, NIVEAUX_FR, STATUTS_FR, ETYPES_FR, NIVEAU } from "../libelles.js";
import { escapeHtml as h } from "../escapeHtml.js";
import { buildEstimatedFootprint } from "../estimatedFootprint.js";
import { roadVisible, missionToHighlight, missionRouteVisible } from "../mapVisibility.js";

const MAP_COLORS = { calm: "#83c2bf", watch: "#d4ab70", danger: "#db8580", muted: "#92a7ad" };
const COULEURS_STATUT = {
  ONLINE: MAP_COLORS.calm,
  OPERATIONAL: MAP_COLORS.calm,
  CLEAR: MAP_COLORS.calm,
  OFFLINE: MAP_COLORS.danger,
  COMPROMISED: MAP_COLORS.watch,
  BLOCKED: MAP_COLORS.watch,
  UNKNOWN: MAP_COLORS.muted,
};

const TAILLES = {
  Hospital: 16,
  PowerStation: 14,
  TelecomTower: 12,
  Warehouse: 13,
  Pharmacy: 10,
  Road: 8,
  Zone: null,
};

const EMOJIS_NATURE = {
  Hospital: "🏥",
  PowerStation: "⚡",
  TelecomTower: "📡",
  Warehouse: "📦",
  Pharmacy: "💊",
  Road: "🛣️",
};

const RISK_COLORS = {
  LOW: MAP_COLORS.muted,
  MEDIUM: MAP_COLORS.watch,
  HIGH: MAP_COLORS.watch,
  CRITICAL: MAP_COLORS.danger,
};

const WHATIF_LINK_EXPLANATIONS = {
  POWER_FAILURE: "Le site dépend directement ou indirectement de l'alimentation du poste ciblé.",
  CYBER_ATTACK: "Une dépendance technique relie le site à la cible de la cyberattaque simulée.",
  ROAD_BLOCKED: "Le modèle relie le site à cette route par un accès ou une chaîne d'approvisionnement.",
  HEAVY_RAIN: "Le modèle relie le site à cette zone météo, directement ou par le réseau routier.",
};

const toLatLngs = (flat) => {
  const out = [];
  for (let i = 0; i + 1 < flat.length; i += 2) out.push([flat[i], flat[i + 1]]);
  return out;
};

export default function MapView({
  infra,
  cibleId,
  searchFocus = null,
  onSelection,
  vaguesCascades = [],
  fantomes = [],
  riskById = {},
  chaineRisque = [],
  sourceRisqueId,
  itineraires = [],
  missions = [],
  featuredMissionId = null,
  options = [],
  notificationFocus = null,
  notificationImpact = null,
  notificationImpactError = null,
  whatifImpact = null,
  selectedWhatifImpact = null,
  onWhatifImpactSelection,
  onCloseWhatifImpact,
  liveRiskImpacts = [],
  onCloseNotification,
  replay = false,
}) {
  const carte = useRef(null);
  const couche = useRef(null);
  const coucheMissions = useRef(null);
  const coucheVariantes = useRef(null);
  const coucheChaine = useRef(null);
  const coucheEstimee = useRef(null);
  const derniereChaine = useRef(null);
  const markers = useRef({});
  const [showRoadNetwork, setShowRoadNetwork] = useState(false);
  const [showAllMissionRoutes, setShowAllMissionRoutes] = useState(false);
  const [selectedMissionId, setSelectedMissionId] = useState(null);
  const focusedMissionId = missionToHighlight(missions, selectedMissionId, featuredMissionId);
  const lastNotificationFocus = useRef(null);
  const liveEstimate = useMemo(() => liveRiskImpacts.length ? { impacts: liveRiskImpacts } : null,
    [liveRiskImpacts]);
  const visibleEstimate = notificationFocus ? notificationImpact : whatifImpact || liveEstimate;
  const whatifById = useMemo(() => new Map((whatifImpact?.impacts || []).map((impact) => [impact.id, impact])),
    [whatifImpact]);
  const selectNode = (node) => {
    const impact = whatifById.get(node.id);
    if (impact && onWhatifImpactSelection) onWhatifImpactSelection(impact);
    else onSelection(node);
  };
  const footprintColor = whatifImpact ? MAP_COLORS.calm : notificationFocus ? MAP_COLORS.calm : MAP_COLORS.watch;
  const footprint = useMemo(() => buildEstimatedFootprint(infra, visibleEstimate?.impacts || []),
    [infra, visibleEstimate]);
  const voirEmprise = () => {
    const points = footprint.groups.flatMap((group) => group.polygon);
    if (points.length) carte.current?.fitBounds(points, { padding: [35, 35], maxZoom: 14 });
  };

  useEffect(() => {
    if (carte.current) return;

    carte.current = L.map("carte", {
      center: [36.825, 10.175],
      zoom: 13,
      zoomControl: true,
    });

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap",
    }).addTo(carte.current);

    couche.current = L.layerGroup().addTo(carte.current);
    coucheMissions.current = L.layerGroup().addTo(carte.current);
    coucheVariantes.current = L.layerGroup().addTo(carte.current);
    coucheChaine.current = L.layerGroup().addTo(carte.current);
    coucheEstimee.current = L.layerGroup().addTo(carte.current);

    const resize = () => carte.current?.invalidateSize();
    setTimeout(resize, 150);
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      carte.current?.remove();
      carte.current = null;
    };
  }, []);

  useEffect(() => {
    if (!couche.current) return;

    couche.current.clearLayers();
    markers.current = {};

    for (const itineraire of itineraires) {
      if (!itineraire.coords || itineraire.coords.length < 2) continue;
      const latlngs = itineraire.coords.map(([lat, lon]) => [lat, lon]);

      L.polyline(latlngs, {
        color: MAP_COLORS.calm,
        weight: 10,
        opacity: 0.16,
        lineCap: "round",
      }).addTo(couche.current);

      const trait = L.polyline(latlngs, {
        color: MAP_COLORS.calm,
        weight: 3.5,
        opacity: 0.95,
        dashArray: "9 6",
        lineCap: "round",
      })
        .addTo(couche.current)
        .bindPopup(
          `<div class="map-popup">` +
            `<b>🧭 Itinéraire alternatif optimal</b><br>` +
            `vers ${h(itineraire.dest_id)} · ${h(itineraire.dest_name)}<br>` +
            `via ${h(itineraire.via_names?.join(" › ") || "…")} ` +
            `(${h(itineraire.jumps)} saut(s))` +
          `</div>`
        );
    }

    for (const node of infra) {
      if (node.lat == null || node.lon == null) continue;

      const risk = riskById[node.id];

      if (node.kind === "Zone") {
        const zoneRisk = risk ? RISK_COLORS[risk.risk] : MAP_COLORS.calm;
        const zone = L.circle([node.lat, node.lon], {
          radius: 1450,
          color: zoneRisk,
          weight: risk ? 2 : 1,
          dashArray: "7 7",
          fillColor: zoneRisk,
          fillOpacity: risk ? 0.08 : 0.035,
        })
          .addTo(couche.current)
          .bindPopup(
            `<b>${h(node.name)}</b><br>Zone météo` +
              (risk ? `<br><b>Risque ${h(NIVEAU(risk.risk))} : ${h(risk.score)}/100</b>` : "")
          );

        zone.on("click", () => selectNode(node));
        markers.current[node.id] = { marker: zone, el: zone.getElement(), pin: null };
        continue;
      }

      const couleur = COULEURS_STATUT[node.status] || COULEURS_STATUT.UNKNOWN;
      const taille = TAILLES[node.kind] || 9;
      const riskColor = risk ? RISK_COLORS[risk.risk] : null;

      // ----- Routes formatees : polyline reelle (trace GPS) -----
      if (node.kind === "Road" && Array.isArray(node.path) && node.path.length >= 4) {
        const pts = [];
        for (let i = 0; i + 1 < node.path.length; i += 2) {
          pts.push([node.path[i], node.path[i + 1]]);
        }
        if (pts.length >= 2) {
          const bloquee = node.status && node.status !== "CLEAR";
          const routeVisible = roadVisible(node, cibleId, showRoadNetwork, replay);

          if (risk && risk.score >= 50) {
            L.polyline(pts, {
              color: riskColor,
              weight: risk.risk === "CRITICAL" ? 9 : 6,
              opacity: 0.16,
              lineCap: "round",
              lineJoin: "round",
              className: risk.risk === "CRITICAL" ? "risk-map-pulse" : "",
            }).addTo(couche.current);
          }

          const popupHtml =
            `<div class="map-popup">` +
              `<b>🛣️ ${h(node.name)}</b><br>` +
              `<span>Route · ${h(node.id)}</span><br>` +
              `Statut : <b>${h(STATUTS_FR[node.status || "UNKNOWN"] || node.status || "Inconnu")}</b><br>` +
              (risk
                ? `Risque : <b style="color:${riskColor}">${h(NIVEAU(risk.risk))} · ${h(risk.score)}/100</b><br>`
                : "Risque : FAIBLE / non exposé<br>") +
              (node.criticality != null ? `Criticité : ${h(node.criticality)}/5<br>` : "") +
            `</div>`;

          if (routeVisible) {
            const route = L.polyline(pts, {
              color: replay || bloquee || node.id === cibleId ? couleur : MAP_COLORS.muted,
              weight: replay ? (node.criticality >= 4 ? 5 : 3) : bloquee || node.id === cibleId ? 3 : 1.5,
              opacity: replay ? 0.8 : bloquee || node.id === cibleId ? 0.85 : 0.35,
              lineCap: "round",
              lineJoin: "round",
              dashArray: bloquee ? "7 9" : undefined,
            })
              .addTo(couche.current)
              .bindPopup(popupHtml);
            route.on("click", () => selectNode(node));
          }

          const pivot = [
            pts.reduce((s, p) => s + p[0], 0) / pts.length,
            pts.reduce((s, p) => s + p[1], 0) / pts.length,
          ];
          const classesPin =
            "ub-pin route-pin" +
            (node.id === cibleId ? " selected" : "") +
            (fantomes.includes(node.id) ? " fantome" : "");
          const badge = L.marker(pivot, {
            interactive: true,
            zIndexOffset: 400,
            icon: L.divIcon({
              className: "",
              iconSize: [16, 16],
              iconAnchor: [8, 8],
              html:
                `<div class="${classesPin}" style="color:${couleur};width:16px;height:16px">` +
                  `<div class="coeur"></div>` +
                  `<div class="etiquette">${h(node.id)}</div>` +
                `</div>`,
            }),
          })
            .addTo(couche.current)
            .bindPopup(popupHtml);

          const badgeEl = badge.getElement();
          badge.on("click", () => selectNode(node));
          markers.current[node.id] = { marker: badge, el: badgeEl, pin: badgeEl };
          continue;
        }
      }

      if (risk && risk.score >= 30) {
        L.circleMarker([node.lat, node.lon], {
          radius: taille + 7,
          color: riskColor,
          weight: risk.risk === "CRITICAL" ? 3 : 2,
          fillColor: riskColor,
          fillOpacity: 0.08,
          opacity: 0.9,
          className: risk.risk === "CRITICAL" ? "risk-map-pulse" : "",
        }).addTo(couche.current);
      }

      const marker = L.circleMarker([node.lat, node.lon], {
        radius: taille + 4,
        color: couleur,
        weight: 1.6,
        opacity: 0.85,
        fillColor: couleur,
        fillOpacity: 0.1,
      })
        .addTo(couche.current)
        .bindPopup(
          `<div class="map-popup">` +
            `<b>${EMOJIS_NATURE[node.kind] || "📍"} ${h(node.name)}</b><br>` +
            `<span>${h(NATURES_FR[node.kind] || node.kind)} · ${h(node.id)}</span><br>` +
            `Statut : <b>${h(STATUTS_FR[node.status || "UNKNOWN"] || node.status || "Inconnu")}</b><br>` +
            (risk
              ? `Risque : <b style="color:${riskColor}">${h(NIVEAU(risk.risk))} · ${h(risk.score)}/100</b><br>`
              : "Risque : FAIBLE / non exposé<br>") +
            (node.criticality != null ? `Criticité : ${h(node.criticality)}/5<br>` : "") +
            (node.backup_power_hours != null
              ? `Secours : ${h(node.backup_power_hours)} h<br>`
              : "") +
            (node.stock_days != null ? `Stock : ${h(node.stock_days)} j` : "") +
          `</div>`
        );

      const el = marker.getElement();
      if (el) {
        const pin = document.createElement("div");
        pin.className =
          "ub-pin" +
          (node.id === cibleId ? " selected" : "") +
          (fantomes.includes(node.id) ? " fantome" : "");

        pin.style =
          `position:absolute;width:24px;height:24px;` +
          `color:${couleur};transform:translate(-50%,-50%);z-index:2;`;

        pin.innerHTML =
          `<div class="coeur"></div>` +
          `<div class="symbole">${EMOJIS_NATURE[node.kind] || "📍"}</div>` +
          `<div class="etiquette">${h(node.id)}</div>`;

        el.appendChild(pin);
        markers.current[node.id] = { marker, el, pin };
      }

      marker.on("click", () => selectNode(node));
    }
    if (searchFocus) markers.current[searchFocus.id]?.marker?.openPopup();
  }, [infra, cibleId, fantomes, riskById, onSelection, itineraires, searchFocus, whatifById, showRoadNetwork, replay]);

  useEffect(() => {
    const layer = coucheChaine.current;
    if (!layer) return;
    layer.clearLayers();
    const positions = new Map(infra.filter((n) => n.lat != null && n.lon != null)
      .map((n) => [n.id, [n.lat, n.lon]]));
    const etapes = chaineRisque.map((n) => positions.get(n.id));
    const pts = etapes.filter(Boolean);
    if (pts.length < 2) {
      derniereChaine.current = null;
      return;
    }
    for (let i = 1; i < etapes.length; i++) {
      if (!etapes[i - 1] || !etapes[i]) continue;
      L.polyline([etapes[i - 1], etapes[i]], {
        color: MAP_COLORS.watch, weight: 4, opacity: 0.95, dashArray: "7 7",
        lineCap: "round",
      }).addTo(layer).bindPopup("Lien de dépendance modélisé — pas un trajet routier");
    }
    pts.forEach((point, index) => {
      L.circleMarker(point, {
        radius: index === 0 ? 8 : 5,
        color: MAP_COLORS.watch, fillColor: index === 0 ? MAP_COLORS.danger : MAP_COLORS.watch,
        fillOpacity: 1, weight: 2,
      }).addTo(layer);
    });
    const cle = `${sourceRisqueId}-${chaineRisque.at(-1)?.id}`;
    if (notificationFocus) {
      derniereChaine.current = cle; // garder le lieu de l'alerte au centre, même après l'analyse asynchrone
      return;
    }
    if (carte.current && !searchFocus && cle !== derniereChaine.current) {
      derniereChaine.current = cle;
      carte.current.fitBounds(pts, { padding: [45, 45], maxZoom: 14, animate: true });
    }
  }, [infra, chaineRisque, sourceRisqueId, notificationFocus, searchFocus]);

  useEffect(() => {
    if (!searchFocus || !carte.current) return;
    const node = infra.find((entry) => entry.id === searchFocus.id);
    if (node?.lat == null || node?.lon == null) return;
    const map = carte.current;
    const showPopup = () => markers.current[node.id]?.marker?.openPopup();
    map.once("moveend", showPopup);
    if (node.kind === "Road" && Array.isArray(node.path) && node.path.length >= 4) {
      const points = toLatLngs(node.path);
      map.fitBounds(points, { padding: [70, 70], maxZoom: 16, animate: true });
    } else {
      map.flyTo([node.lat, node.lon], Math.max(map.getZoom(), 15), { duration: 0.8 });
    }
    showPopup();
    return () => map.off("moveend", showPopup);
  }, [infra, searchFocus]);

  useEffect(() => {
    if (!notificationFocus || !carte.current || lastNotificationFocus.current === notificationFocus.focusKey) return;
    const node = infra.find((entry) => entry.id === notificationFocus.location_id);
    if (node?.lat == null || node?.lon == null) return;
    lastNotificationFocus.current = notificationFocus.focusKey;
    carte.current.flyTo([node.lat, node.lon], Math.max(carte.current.getZoom(), 15), { duration: 0.8 });
  }, [infra, notificationFocus]);

  useEffect(() => {
    const layer = coucheEstimee.current;
    if (!layer) return;
    layer.clearLayers();
    if (!visibleEstimate) return;
    for (const group of footprint.groups) {
      L.polygon(group.polygon, {
        color: footprintColor, weight: 2, dashArray: "8 6", fillColor: footprintColor,
        fillOpacity: 0.08, interactive: false,
      }).addTo(layer);
    }
    const positions = new Map(infra.map((node) => [node.id, node]));
    for (const impact of visibleEstimate.impacts) {
      const node = positions.get(impact.id);
      if (node?.lat == null || node?.lon == null) continue;
      const bubble = L.circleMarker([node.lat, node.lon], {
        radius: 25, color: RISK_COLORS[impact.risk] || RISK_COLORS.LOW,
        weight: 2, dashArray: "5 5", fillOpacity: 0.04,
      }).addTo(layer).bindPopup(
        `<div class="map-popup"><b>Impact estimé · ${h(node.name)}</b><br>` +
        `Risque calculé : ${h(NIVEAU(impact.risk))} · ${h(impact.score)}/100<br>` +
        `Projection du modèle, pas un dommage constaté.</div>`
      );
      if (whatifImpact && onWhatifImpactSelection) bubble.on("click", () => onWhatifImpactSelection(impact));
    }
  }, [infra, visibleEstimate, footprint, footprintColor, whatifImpact, onWhatifImpactSelection]);

  useEffect(() => {
    if (!vaguesCascades?.length) return;

    const timers = [];

    for (const { id, depth, score } of vaguesCascades) {
      timers.push(
        setTimeout(() => {
          const entry = markers.current[id];
          if (!entry?.el) return;

          const couleur =
            score >= 70 ? MAP_COLORS.danger : score >= 50 ? MAP_COLORS.watch : MAP_COLORS.calm;

          const onde = document.createElement("div");
          onde.className = "onde";
          onde.style.color = couleur;
          entry.el.appendChild(onde);

          timers.push(setTimeout(() => onde.remove(), 1700));
        }, 250 + depth * 850)
      );
    }

    return () => timers.forEach(clearTimeout);
  }, [vaguesCascades]);

  useEffect(() => {
    const layer = coucheMissions.current;
    if (!layer) return;
    layer.clearLayers();

    for (const mission of missions) {
      const path = mission.path || [];
      if (path.length < 4) continue;
      const highlighted = replay || mission.mission_id === focusedMissionId;

      const couleur =
        mission.status === "BLOCKED" ? MAP_COLORS.danger : mission.status === "DIVERTED" ? MAP_COLORS.watch : MAP_COLORS.calm;

      const latlngs = toLatLngs(path);

      if (missionRouteVisible(mission.mission_id, focusedMissionId, showAllMissionRoutes, replay)) {
        if (highlighted) L.polyline(latlngs, {
          color: couleur,
          weight: 9,
          opacity: 0.12,
          lineCap: "round",
        }).addTo(layer);

        L.polyline(latlngs, {
          color: highlighted ? couleur : MAP_COLORS.muted,
          weight: highlighted ? 3.5 : 1.5,
          opacity: highlighted ? 0.95 : 0.3,
          dashArray: mission.status === "DIVERTED" ? "8 7" : null,
          lineCap: "round",
        })
          .addTo(layer)
          .bindPopup(
            `<div class="map-popup">` +
              `<b>${mission.corridor_active ? "🚨 " : ""}Mission ${h(mission.mission_id)} · ${h(PROFILS_FR[mission.profile] || mission.profile)}</b><br>` +
              `${mission.vehicle ? `Véhicule <b>${h(mission.vehicle)}</b> · ` : ""}` +
              `${h(mission.origin_name)} → ${h(mission.destination_name)}<br>` +
              `${h((Number(mission.progress || 0) * 100).toFixed(0))}% · arrivée dans ${h(mission.remaining_min)} min` +
            `</div>`
          );
      }

      const [lat, lon] = mission.position || [];
      if (lat != null && lon != null) {
        const emoji = mission.profile === "SUPPLY" ? "🚚" : "🚑";
        L.marker([lat, lon], {
          zIndexOffset: 700,
          icon: L.divIcon({
            className: "ub-vehicle-icon",
            html: `<div class="ub-vehicle${mission.corridor_active ? " sirene" : ""}" style="--c:${couleur}">${emoji}</div>`,
            iconSize: [30, 30],
            iconAnchor: [15, 15],
          }),
        }).addTo(layer);
      }
    }
  }, [missions, focusedMissionId, showAllMissionRoutes, replay]);

  // ----- les 3 variantes du comparateur (FAST / SHORT / SAFE) -----
  useEffect(() => {
    const layer = coucheVariantes.current;
    if (!layer) return;
    layer.clearLayers();

    const couleurs = { FAST: MAP_COLORS.calm, SHORT: MAP_COLORS.muted, SAFE: MAP_COLORS.watch };

    for (const option of options) {
      const path = option.path || [];
      if (path.length < 4) continue;

      const latlngs = toLatLngs(path);
      const couleur = couleurs[option.variant] || MAP_COLORS.calm;
      const label = { FAST: "🟢 Rapide", SHORT: "🔵 Court", SAFE: "🟠 Sûr" }[option.variant] || option.variant;

      L.polyline(latlngs, {
        color: couleur,
        weight: 9,
        opacity: 0.1,
        lineCap: "round",
      }).addTo(layer);

      L.polyline(latlngs, {
        color: couleur,
        weight: 2.6,
        opacity: 0.9,
        dashArray: "10 8",
        lineCap: "round",
      })
        .addTo(layer)
        .bindPopup(
          `<div class="map-popup">` +
            `<b>${label}</b><br>` +
            `${h(option.estimated_time_min)} min · ${h(option.distance_km)} km<br>` +
            `${h(option.route_names?.join(" › ") || "")}` +
          `</div>`
        );
    }
  }, [options]);

  return (
    <>
      <div id="carte" />
      {whatifImpact && selectedWhatifImpact && (
        <div className="map-whatif-explanation" role="region" aria-label="Explication de l'impact hypothétique">
          <button className="map-notification-close" onClick={onCloseWhatifImpact}
            aria-label="Fermer l'explication de l'impact">×</button>
          <small>SCÉNARIO HYPOTHÉTIQUE · AUCUN DOMMAGE CONSTATÉ</small>
          <strong>{selectedWhatifImpact.name} · {selectedWhatifImpact.id}</strong>
          <p>Si {ETYPES_FR[whatifImpact.event_type] || whatifImpact.event_type} sur {whatifImpact.target_id} se produisait (intensité {NIVEAU(whatifImpact.severity)}), ce site pourrait être concerné selon le graphe.</p>
          <p>{WHATIF_LINK_EXPLANATIONS[whatifImpact.event_type] || "Un lien du graphe relie le site à la cible de l'incident simulé."}</p>
          <b>Chaîne modélisée · {selectedWhatifImpact.depth} {selectedWhatifImpact.depth > 1 ? "liens" : "lien"}</b>
          <div className="whatif-explanation-chain">{selectedWhatifImpact.chain?.map((step) => step.name || step.id).join(" → ") || "Chemin non disponible"}</div>
          <b>Pourquoi ce niveau de risque estimé ? {NIVEAU(selectedWhatifImpact.risk)} · {selectedWhatifImpact.score}/100</b>
          {selectedWhatifImpact.reasons?.length > 0 && <ul>
            {selectedWhatifImpact.reasons.map((reason, index) => <li key={index}>{reason}</li>)}
          </ul>}
          <span>Projection du modèle, pas une panne, un blocage ou un dégât observé. Aucun état de la ville n'a été modifié.</span>
        </div>
      )}
      {notificationFocus && (
        <div className="map-notification-focus" role="region" aria-label="Explication de la notification sur la carte">
          <button className="map-notification-close" onClick={onCloseNotification}
            aria-label="Fermer l'explication">×</button>
          <small>{notificationFocus.category === "INCIDENT" ? "INCIDENT ENREGISTRÉ" :
            notificationFocus.category === "CALL" ? "APPEL REÇU" : "MISSION SIMULÉE"} · {NIVEAU(notificationFocus.severity)}</small>
          <strong>{notificationFocus.title} · {notificationFocus.location_id}</strong>
          <p>{notificationFocus.detail}</p>
          <span>Source : {notificationFocus.producer} · {new Date(notificationFocus.created_at).toLocaleString("fr-FR")}</span>
          {notificationFocus.category === "INCIDENT" && notificationFocus.state !== "RESOLVED" && (
            <div className="map-estimated-impact">
              <b>ESTIMATION DU MODÈLE · pas de dommage constaté</b>
              {notificationImpact ? (
                <>
                  <span>{notificationImpact.total_count} site(s) potentiellement touché(s) · calcul sur l'état actuel</span>
                  <span>{notificationImpact.impacts.slice(0, 4).map((impact) => impact.name).join(" · ") || "Aucun site exposé selon le modèle."}</span>
                  <span>{footprint.groups.length} emprise(s) indicatives · incertitude qualitative {footprint.uncertainty.toLowerCase()} ({footprint.reason}).</span>
                  <span>Contours en pointillés : enveloppes de lecture autour des sites, pas des zones entièrement sinistrées.</span>
                  {footprint.groups.length > 0 && <button className="map-fit-estimate" onClick={voirEmprise}>Voir toutes les emprises estimées</button>}
                </>
              ) : <span>{notificationImpactError || "Calcul de l'impact potentiel…"}</span>}
            </div>
          )}
          {notificationFocus.category !== "INCIDENT" && <span>Aucun impact potentiel calculé pour cette alerte.</span>}
          {notificationFocus.state === "RESOLVED" && <span>Incident clos : aucune projection actuelle affichée.</span>}
        </div>
      )}
      {!notificationFocus && visibleEstimate && (
        <div className="map-estimate-overview" role="region" aria-label="Emprise estimée du modèle" style={{ borderColor: footprintColor }}>
          <b style={{ color: footprintColor }}>{whatifImpact ? "🔮 SCÉNARIO HYPOTHÉTIQUE" : "◌ RISQUES CALCULÉS · ÉTAT ACTUEL"}</b>
          <span>{footprint.groups.length} emprise(s) indicatives autour de {footprint.mappedCount} site(s) · incertitude {footprint.uncertainty.toLowerCase()}.</span>
          <small>{footprint.reason}. {whatifImpact ? "Aucune crise modifiée ; les contours" : "Les contours"} ne prédisent pas une zone de dégâts.</small>
          {footprint.groups.length > 0 && <button onClick={voirEmprise} style={{ borderColor: footprintColor, color: footprintColor }}>Voir les emprises estimées</button>}
        </div>
      )}
      <div className="map-overlay-title">
         <small>{replay ? "ARCHIVE OBSERVÉE // PAS EN DIRECT" : "JUMEAU NUMÉRIQUE EN DIRECT"}</small>
        <b>Grand Tunis</b>
      </div>
      {!replay && <div className="map-visibility" role="group" aria-label="Lisibilité de la carte">
        <label><input type="checkbox" checked={showRoadNetwork}
          onChange={(event) => setShowRoadNetwork(event.target.checked)} /> Routes de fond</label>
        {missions.length > 1 && <>
          <label><input type="checkbox" checked={showAllMissionRoutes}
            onChange={(event) => setShowAllMissionRoutes(event.target.checked)} /> Tous les trajets</label>
          <select aria-label="Mission mise en évidence" value={focusedMissionId || ""}
            onChange={(event) => setSelectedMissionId(event.target.value)}>
            {missions.map((mission) => <option key={mission.mission_id} value={mission.mission_id}>
              {mission.vehicle || mission.mission_id} · {mission.mission_id}
            </option>)}
          </select>
        </>}
      </div>}

      <div className="legende">
        <div className="legende-titre">Risque calculé</div>
        <span><i className="puce risk-low-dot" /> {NIVEAUX_FR.LOW}</span>
        <span><i className="puce risk-medium-dot" /> {NIVEAUX_FR.MEDIUM}</span>
        <span><i className="puce risk-high-dot" /> {NIVEAUX_FR.HIGH}</span>
        <span><i className="puce risk-critical-dot" /> {NIVEAUX_FR.CRITICAL}</span>

        <div className="legende-titre legend-gap">Statut opérationnel</div>
        <span><i className="puce status-ok-dot" /> Opérationnel</span>
        <span><i className="puce status-down-dot" /> Hors service</span>
        <span><i className="puce status-cyber-dot" /> Compromis</span>
        <span><i className="puce whatif-dot" /> Simulation</span>
        {chaineRisque.length > 1 && <span><i className="puce chaine-dot" /> Dépendance estimée</span>}
        {visibleEstimate && <span><i className="puce footprint-dot" style={{ backgroundColor: footprintColor, borderColor: footprintColor }} /> Emprise indicative (modèle)</span>}
      </div>
    </>
  );
}
