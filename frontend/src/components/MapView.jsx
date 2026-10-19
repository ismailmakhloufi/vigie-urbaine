import { useEffect, useRef } from "react";
import L from "leaflet";

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
  Hospital: 20,
  PowerStation: 18,
  TelecomTower: 15,
  Warehouse: 16,
  Pharmacy: 13,
  Road: 11,
  Zone: null,
};

function iconePin(couleur, statut, critique, selectionne, fantome) {
  const classes = ["ub-pin"];
  if (selectionne) classes.push("selected");
  if (fantome) classes.push("fantome");
  if (critique && statut !== "ONLINE") classes.push("critique-neon");
  return L.divIcon({
    className: "",
    iconSize: [30, 30],
    html: `<div class="${classes.join(" ")}" style="color:${couleur}">
             <div class="coeur"></div>
           </div>`,
  });
}

export default function MapView({
  infra,
  cibleId,
  onSelection,
  vaguesCascades,
  fantomes,
}) {
  const carte = useRef(null);
  const couche = useRef(null);
  const markers = useRef({});

  useEffect(() => {
    if (carte.current) return;
    carte.current = L.map("carte", { center: [36.825, 10.175], zoom: 13 });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap",
    }).addTo(carte.current);
    couche.current = L.layerGroup().addTo(carte.current);
    setTimeout(() => carte.current.invalidateSize(), 200);
    window.addEventListener("resize", () => carte.current.invalidateSize());
  }, []);

  useEffect(() => {
    if (!couche.current) return;
    couche.current.clearLayers();
    markers.current = {};

    for (const node of infra) {
      if (node.kind === "Zone") {
        const zone = L.circle([node.lat, node.lon], {
          radius: 1600,
          color: "#22d3ee",
          weight: 1,
          dashArray: "6 6",
          fillColor: "#22d3ee",
          fillOpacity: 0.05,
        })
          .addTo(couche.current)
          .bindPopup(
            `<b>Zone ${node.name}</b><br>Ciblée par la pluie extrême 🌧` +
              (node.status && node.status !== "ONLINE" ? `<br>ALERTE MÉTÉO ACTIVE` : "")
          );
        const el = zone.getElement();
        if (el) {
          const pin = document.createElement("div");
          pin.style = "position:relative;z-index:2;display:inline-block;display:none;";
          el.appendChild(pin);
          markers.current[node.id] = { marker: zone, el, pin };
        }
        zone.on("click", () => onSelection(node));
        continue;
      }

      const couleur = COULEURS_STATUT[node.status] || COULEURS_STATUT.UNKNOWN;
      const taille = TAILLES[node.kind] || 10;
      const critique = node.criticality >= 4;
      const marker = L.circleMarker([node.lat, node.lon], {
        radius: taille,
        color: couleur,
        weight: 2,
        fillColor: couleur,
        fillOpacity: 0.55,
      })
        .addTo(couche.current)
        .bindPopup(
          `<b>${node.name}</b><br>` +
            `Type : ${node.kind}<br>` +
            `Statut : ${node.status}<br>` +
            (node.criticality ? `Criticité : ${node.criticality}/5<br>` : "") +
            (node.backup_power_hours !== undefined
              ? `Gén. secours : ${node.backup_power_hours} h<br>`
              : "") +
            (node.stock_days !== undefined
              ? `Stock médicaments : ${node.stock_days} j`
              : "")
        );

      const el = marker.getElement();
      if (el) {
        const pin = document.createElement("div");
        pin.className =
          "ub-pin" +
          (node.id === cibleId ? " selected" : "") +
          (critique && node.status !== "ONLINE" ? " critique-neon" : "");
        pin.style =
          `position:absolute;width:24px;height:24px;` +
          `color:${couleur};transform:translate(-50%,-50%);z-index:2;`;
        pin.innerHTML = `<div class="coeur"></div><div class="etiquette">${node.id}</div>`;
        el.appendChild(pin);
        markers.current[node.id] = { marker, el, pin };
      }
      marker.on("click", () => onSelection(node));
    }
  }, [infra, cibleId]);

  useEffect(() => {
    if (!vaguesCascades || vaguesCascades.length === 0) return;
    const timers = [];
    for (const { id, depth, score } of vaguesCascades) {
      timers.push(
        setTimeout(
          () => {
            const entry = markers.current[id];
            if (!entry) return;
            const couleur =
              score >= 70 ? "#f43f5e" : score >= 50 ? "#fbbf24" : "#22d3ee";
            const onde = document.createElement("div");
            onde.className = "onde";
            onde.style.color = couleur;
            entry.el.appendChild(onde);
            timers.push(
              setTimeout(() => onde.remove(), 1700)
            );
          },
          250 + depth * 900
        )
      );
    }
    return () => timers.forEach(clearTimeout);
  }, [vaguesCascades]);

  useEffect(() => {
    for (const [id, entry] of Object.entries(markers.current)) {
      if (entry.pin) entry.pin.classList.toggle("fantome", fantomes.includes(id));
    }
  }, [fantomes, infra]);

  return (
    <>
      <div id="carte" />
      <div className="legende">
        <span><i className="puce" style={{ background: "#34d399" }} /> Opérationnel</span>
        <span><i className="puce" style={{ background: "#fbbf24" }} /> Route bloquée</span>
        <span><i className="puce" style={{ background: "#f43f5e" }} /> Hors service</span>
        <span><i className="puce" style={{ background: "#f472b6" }} /> Compromis (cyber)</span>
        <span><i className="puce" style={{ border: "2px dashed #a78bfa", background: "transparent" }} /> Prédiction What-if</span>
      </div>
    </>
  );
}
