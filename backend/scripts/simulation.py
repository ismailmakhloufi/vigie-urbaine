"""Commandes manuelles de simulation via l'API locale, sans enchaînement automatique."""

import argparse
import getpass
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="Adresse de l'API")
    parser.add_argument("--connexion", action="store_true", help="Demander le mot de passe opérateur")
    sub = parser.add_subparsers(dest="command", required=True)

    incident = sub.add_parser("incident", help="Enregistrer un incident simulé")
    incident.add_argument("type", choices=["pluie", "panne", "cyber", "route"])
    incident.add_argument("cible", help="Identifiant de la zone, du poste, du site ou de la route")
    incident.add_argument("--gravite", choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"], default="HIGH")
    appel = sub.add_parser("appel", help="Déclencher un appel SAMU fictif")
    appel.add_argument("hopital")
    sub.add_parser("missions", help="Afficher les missions et leur trajet")
    detours = sub.add_parser("detours", help="Routes à bloquer encore devant la mission, avec détour court")
    detours.add_argument("mission")
    comparer = sub.add_parser("comparer", help="Comparer les variantes depuis la position courante")
    comparer.add_argument("mission")
    court = sub.add_parser("court", help="Appliquer la variante la plus courte à la mission")
    court.add_argument("mission")
    resoudre = sub.add_parser("resoudre", help="Résoudre un incident par son identifiant")
    resoudre.add_argument("incident_id")
    args = parser.parse_args()

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(path, data=None):
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(args.api.rstrip("/") + path, data=body,
                                     headers={"Content-Type": "application/json"})
        with opener.open(req, timeout=30) as response:
            return json.load(response)

    try:
        if args.connexion:
            request("/auth/login", {"username": "operateur", "password": getpass.getpass("Mot de passe opérateur : ")})
        if args.command == "incident":
            kind = {"pluie": "HEAVY_RAIN", "panne": "POWER_FAILURE", "cyber": "CYBER_ATTACK", "route": "ROAD_BLOCKED"}[args.type]
            result = request("/events", {"type": kind, "target_id": args.cible.upper(),
                                        "severity": args.gravite, "description": "Incident fictif déclenché depuis le terminal"})
        elif args.command == "appel":
            result = request("/demo/medical-call", {"destination_id": args.hopital.upper()})
        elif args.command == "missions":
            result = request("/missions")
        elif args.command == "detours":
            result = request(f"/missions/{args.mission}/demo-detours")
        elif args.command == "comparer":
            result = request(f"/missions/{args.mission}/route-options")
        elif args.command == "court":
            result = request(f"/missions/{args.mission}/choose-route", {"variant": "SHORT"})
        else:
            result = request(f"/events/{args.incident_id}/resolve", {})
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (urllib.error.URLError, ValueError) as exc:
        if isinstance(exc, urllib.error.HTTPError):
            detail = exc.read().decode("utf-8", errors="replace")
            print(f"Erreur API {exc.code} : {detail}", file=sys.stderr)
        else:
            print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
