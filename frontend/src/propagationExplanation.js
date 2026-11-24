export function propagationExplanation(source) {
  if (!source) return null;
  if (source.type === "ROAD_BLOCKED") {
    return {
      effect: source.chain?.some((step) => step.kind === "Warehouse")
        ? "Retard d'approvisionnement possible via un dépôt, sans rupture de stock constatée."
        : "Gêne d'accès possible ; le site n'est pas considéré comme en panne.",
      uncertainty: "Accès et détours issus d'un graphe schématique non validé sur le terrain ; une autre voie réelle peut exister.",
    };
  }
  if (source.type === "HEAVY_RAIN") {
    return {
      effect: "Exposition possible dans la zone signalée ; ni inondation du site ni coupure de route constatée.",
      uncertainty: "La zone est approximative. Aucun débordement hors zone n'est inféré par les liens routiers.",
    };
  }
  return {
    effect: "Effet potentiel selon les dépendances techniques déclarées, non une panne observée du site.",
    uncertainty: "Dépendances déclarées dans le graphe de démonstration ; état local et secours à confirmer.",
  };
}
