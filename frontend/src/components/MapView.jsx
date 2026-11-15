import { useEffect, useRef } from "react";
import L from "leaflet";
import { NATURES_FR, PROFILS_FR, NIVEAUX_FR, STATUTS_FR, NIVEAU } from "../libelles.js";

const COULEURS_STATUT = {
  ONLINE: "#34d399",
  OPERATIONAL: "#34d399",
  CLEAR: "#34d399",
  OFFLINE: "#f43f5e",
  COMPROMISED: "#f472b6",
  BLOCKED: "#fbbf24",
  UNKNOWN: "#22d3ee",
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
  LOW: "#22d3ee",
  MEDIUM: "#facc15",
  HIGH: "#f59e0b",
  CRITICAL: "#f43f5e",
};

const toLatLngs = (flat) => {
  const out = [];
  for (let i = 0; i + 1 < flat.length; i += 2) out.push([flat[i], flat[i + 1]]);
  return out;
};

export default function MapView({
  infra,
  cibleId,
  onSelection,
  vaguesCascades = [],
  fantomes = [],
  riskById = {},
  chaineRisque = [],
  sourceRisqueId,
  itineraires = [],
  missions = [],
  options = [],
  replay = false,
}) {
  const carte = useRef(null);
  const couche = useRef(null);
  const coucheMissions = useRef(null);
  const coucheVariantes = useRef(null);
  const coucheChaine = useRef(null);
  const derniereChaine = useRef(null);
  const markers = useRef({});

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
        color: "#67e8f9",
        weight: 10,
        opacity: 0.16,
        lineCap: "round",
      }).addTo(couche.current);

      const trait = L.polyline(latlngs, {
        color: "#67e8f9",
        weight: 3.5,
        opacity: 0.95,
        dashArray: "9 6",
        lineCap: "round",
      })
        .addTo(couche.current)
        .bindPopup(
          `<div class="map-popup">` +
            `<b>🧭 Itinéraire alternatif optimal</b><br>` +
            `vers ${itineraire.dest_id} · ${itineraire.dest_name}<br>` +
            `via ${itineraire.via_names?.join(" › ") || "…"} ` +
            `(${itineraire.jumps} saut(s))` +
          `</div>`
        );
    }

    for (const node of infra) {
      if (node.lat == null || node.lon == null) continue;

      const risk = riskById[node.id];

      if (node.kind === "Zone") {
        const zoneRisk = risk ? RISK_COLORS[risk.risk] : "#22d3ee";
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
            `<b>${node.name}</b><br>Zone météo` +
              (risk ? `<br><b>Risque ${NIVEAU(risk.risk)} : ${risk.score}/100</b>` : "")
          );

        zone.on("click", () => onSelection(node));
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

          if (risk && risk.score >= 30) {
            L.polyline(pts, {
              color: riskColor,
              weight: risk.risk === "CRITICAL" ? 13 : 9,
              opacity: 0.2,
              lineCap: "round",
              lineJoin: "round",
              className: risk.risk === "CRITICAL" ? "risk-map-pulse" : "",
            }).addTo(couche.current);
          }

          const popupHtml =
            `<div class="map-popup">` +
              `<b>🛣️ ${node.name}</b><br>` +
              `<span>Route · ${node.id}</span><br>` +
              `Statut : <b>${STATUTS_FR[node.status || "UNKNOWN"] || node.status || "Inconnu"}</b><br>` +
              (risk
                ? `Risque : <b style="color:${riskColor}">${NIVEAU(risk.risk)} · ${risk.score}/100</b><br>`
                : "Risque : FAIBLE / non exposé<br>") +
              (node.criticality != null ? `Criticité : ${node.criticality}/5<br>` : "") +
            `</div>`;

          const route = L.polyline(pts, {
            color: couleur,
            weight: node.criticality >= 4 ? 5 : 3,
            opacity: 0.8,
            lineCap: "round",
            lineJoin: "round",
            dashArray: bloquee ? "7 9" : undefined,
          })
            .addTo(couche.current)
            .bindPopup(popupHtml);
          route.on("click", () => onSelection(node));

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
                  `<div class="etiquette">${node.id}</div>` +
                `</div>`,
            }),
          })
            .addTo(couche.current)
            .bindPopup(popupHtml);

          const badgeEl = badge.getElement();
          badge.on("click", () => onSelection(node));
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
            `<b>${EMOJIS_NATURE[node.kind] || "📍"} ${node.name}</b><br>` +
            `<span>${NATURES_FR[node.kind] || node.kind} · ${node.id}</span><br>` +
            `Statut : <b>${STATUTS_FR[node.status || "UNKNOWN"] || node.status || "Inconnu"}</b><br>` +
            (risk
              ? `Risque : <b style="color:${riskColor}">${NIVEAU(risk.risk)} · ${risk.score}/100</b><br>`
              : "Risque : FAIBLE / non exposé<br>") +
            (node.criticality != null ? `Criticité : ${node.criticality}/5<br>` : "") +
            (node.backup_power_hours != null
              ? `Secours : ${node.backup_power_hours} h<br>`
              : "") +
            (node.stock_days != null ? `Stock : ${node.stock_days} j` : "") +
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
          `<div class="etiquette">${node.id}</div>`;

        el.appendChild(pin);
        markers.current[node.id] = { marker, el, pin };
      }

      marker.on("click", () => onSelection(node));
    }
  }, [infra, cibleId, fantomes, riskById, onSelection, itineraires]);

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
        color: "#ffb020", weight: 4, opacity: 0.95, dashArray: "7 7",
        lineCap: "round",
      }).addTo(layer).bindPopup("Lien de dépendance modélisé — pas un trajet routier");
    }
    pts.forEach((point, index) => {
      L.circleMarker(point, {
        radius: index === 0 ? 8 : 5,
        color: "#ffb020", fillColor: index === 0 ? "#ff4d5e" : "#ffb020",
        fillOpacity: 1, weight: 2,
      }).addTo(layer);
    });
    const cle = `${sourceRisqueId}-${chaineRisque.at(-1)?.id}`;
    if (carte.current && cle !== derniereChaine.current) {
      derniereChaine.current = cle;
      carte.current.fitBounds(pts, { padding: [45, 45], maxZoom: 14, animate: true });
    }
  }, [infra, chaineRisque, sourceRisqueId]);

  useEffect(() => {
    if (!vaguesCascades?.length) return;

    const timers = [];

    for (const { id, depth, score } of vaguesCascades) {
      timers.push(
        setTimeout(() => {
          const entry = markers.current[id];
          if (!entry?.el) return;

          const couleur =
            score >= 70 ? "#f43f5e" : score >= 50 ? "#f59e0b" : "#22d3ee";

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

      const couleur =
        mission.status === "BLOCKED" ? "#f43f5e" : mission.status === "DIVERTED" ? "#22d3ee" : "#34d399";

      const latlngs = toLatLngs(path);

      L.polyline(latlngs, {
        color: couleur,
        weight: 11,
        opacity: 0.13,
        lineCap: "round",
      }).addTo(layer);

      L.polyline(latlngs, {
        color: couleur,
        weight: 3,
        opacity: 0.85,
        dashArray: mission.status === "DIVERTED" ? "8 7" : null,
        lineCap: "round",
      })
        .addTo(layer)
        .bindPopup(
          `<div class="map-popup">` +
            `<b>${mission.corridor_active ? "🚨 " : ""}Mission ${mission.mission_id} · ${PROFILS_FR[mission.profile] || mission.profile}</b><br>` +
            `${mission.vehicle ? `Véhicule <b>${mission.vehicle}</b> · ` : ""}` +
            `${mission.origin_name} → ${mission.destination_name}<br>` +
            `${(mission.progress * 100).toFixed(0)}% · arrivée dans ${mission.remaining_min} min` +
          `</div>`
        );

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
  }, [missions]);

  // ----- les 3 variantes du comparateur (FAST / SHORT / SAFE) -----
  useEffect(() => {
    const layer = coucheVariantes.current;
    if (!layer) return;
    layer.clearLayers();

    const couleurs = { FAST: "#34d399", SHORT: "#60a5fa", SAFE: "#fb923c" };

    for (const option of options) {
      const path = option.path || [];
      if (path.length < 4) continue;

      const latlngs = toLatLngs(path);
      const couleur = couleurs[option.variant] || "#a78bfa";
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
            `${option.estimated_time_min} min · ${option.distance_km} km<br>` +
            `${option.route_names?.join(" › ") || ""}` +
          `</div>`
        );
    }
  }, [options]);

  return (
    <>
      <div id="carte" />
      <div className="map-overlay-title">
         <small>{replay ? "ARCHIVE OBSERVÉE // PAS EN DIRECT" : "JUMEAU NUMÉRIQUE EN DIRECT"}</small>
        <b>Grand Tunis</b>
      </div>

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
      </div>
    </>
  );
}
