import React from "react";
import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "leaflet/dist/leaflet.css";
import "./styles.css";
import App from "./App.jsx";
import { getSecurityConfig, getCurrentUser, signIn, signOut } from "./api.js";

function SecureApp() {
  const [mode, setMode] = useState("loading");
  const [session, setSession] = useState(null);
  const [username, setUsername] = useState("operateur");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    getSecurityConfig().then(async (config) => {
      if (!config.secure) return active && setMode("demo");
      try {
        const actor = await getCurrentUser();
        if (active) setSession(actor);
      } catch { /* Session absente ou expirée. */ }
      if (active) setMode("secure");
    }).catch(() => { if (active) setMode("error"); });
    const expired = () => setSession(null);
    window.addEventListener("ub-session-expired", expired);
    return () => { active = false; window.removeEventListener("ub-session-expired", expired); };
  }, []);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setSession(await signIn(username, password));
      setPassword("");
    } catch (exc) { setError(exc.message); }
    finally { setBusy(false); }
  }

  if (mode === "loading") return <div className="auth-screen">Connexion au poste de commandement…</div>;
  if (mode === "error") return <div className="auth-screen">API indisponible. Vérifiez le serveur et rechargez cette page.</div>;
  if (mode === "demo") return <App />;
  if (!session) return (
    <main className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <small>VIGIE URBAINE // ACCÈS CONTRÔLÉ</small>
        <h1>Poste de commandement</h1>
        <p>Simulation urbaine du Grand Tunis. Accès réservé aux comptes autorisés.</p>
        <label>Identifiant
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </label>
        <label>Mot de passe
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </label>
        {error && <div role="alert" className="auth-error">{error}</div>}
        <button disabled={busy}>{busy ? "Vérification…" : "Ouvrir la console"}</button>
        <small>Comptes : opérateur ou observateur (lecture seule).</small>
      </form>
    </main>
  );
  return <>
    <div className="auth-bar">Session : {session.name} · {session.role === "viewer" ? "LECTURE SEULE" : "OPÉRATEUR"}
      <button onClick={async () => { try { await signOut(); } finally { setSession(null); } }}>Déconnexion</button>
    </div>
    <App key={session.name} readonly={session.role === "viewer"} secured />
  </>;
}

createRoot(document.getElementById("root")).render(<SecureApp />);
