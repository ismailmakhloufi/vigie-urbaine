import { useEffect, useMemo, useRef, useState } from "react";
import { NATURES_FR } from "../libelles.js";
import { searchInfrastructure } from "../infrastructureSearch.js";

const MAX_VISIBLE_RESULTS = 8;

export default function InfrastructureSearch({ infrastructure, onChoose }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const container = useRef(null);
  const input = useRef(null);
  const results = useRef(null);
  const matches = useMemo(() => searchInfrastructure(infrastructure, query), [infrastructure, query]);
  const visibleMatches = matches.slice(0, MAX_VISIBLE_RESULTS);
  const showingResults = open && !!query.trim();

  useEffect(() => {
    if (showingResults && active >= 0) results.current?.children[active]?.scrollIntoView({ block: "nearest" });
  }, [active, showingResults]);

  const choose = (node) => {
    setQuery(node.name);
    setOpen(false);
    setActive(-1);
    onChoose(node);
  };

  const onKeyDown = (event) => {
    if (event.key === "Escape") {
      setOpen(false);
      setActive(-1);
      input.current?.blur();
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!query.trim() || !visibleMatches.length) return;
      event.preventDefault();
      setOpen(true);
      setActive((index) => event.key === "ArrowDown"
        ? Math.min(index + 1, visibleMatches.length - 1) : Math.max(index - 1, 0));
    }
    if (event.key === "Home" && showingResults && visibleMatches.length) {
      event.preventDefault();
      setActive(0);
    }
    if (event.key === "End" && showingResults && visibleMatches.length) {
      event.preventDefault();
      setActive(visibleMatches.length - 1);
    }
    if (event.key === "Enter" && showingResults && visibleMatches.length) {
      event.preventDefault();
      choose(visibleMatches[active < 0 ? 0 : active]);
    }
  };

  return (
    <div className={`infrastructure-search ${showingResults ? "search-open" : ""}`} ref={container}
      onBlur={(event) => { if (!container.current?.contains(event.relatedTarget)) setOpen(false); }}>
      <label htmlFor="infrastructure-search-input">Rechercher un lieu <span>sur la carte</span></label>
      <div className="infrastructure-search-field">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
          <circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 5 5" />
        </svg>
        <input id="infrastructure-search-input" ref={input} role="combobox" type="search"
          autoComplete="off" aria-autocomplete="list" aria-expanded={showingResults}
          aria-controls={showingResults ? "infrastructure-search-results" : undefined}
          aria-activedescendant={showingResults && active >= 0 ? `infrastructure-result-${active}` : undefined}
          placeholder="Nom, identifiant ou type de lieu…"
          value={query} onFocus={() => setOpen(true)} onKeyDown={onKeyDown}
          onChange={(event) => { setQuery(event.target.value); setActive(-1); setOpen(true); }} />
        {query && <button type="button" className="infrastructure-search-clear" aria-label="Effacer la recherche"
          onClick={() => { setQuery(""); setActive(-1); setOpen(false); input.current?.focus(); }}>✕</button>}
      </div>
      {showingResults && <div className="infrastructure-results-panel">
        <div className="infrastructure-results-meta" role="status">
          <span>{matches.length} lieu{matches.length > 1 ? "x" : ""} trouvé{matches.length > 1 ? "s" : ""}</span>
          {matches.length > MAX_VISIBLE_RESULTS && <small>Les {MAX_VISIBLE_RESULTS} premiers</small>}
        </div>
        <div id="infrastructure-search-results" className="infrastructure-results" role="listbox" aria-label="Lieux trouvés" ref={results}>
          {visibleMatches.length ? visibleMatches.map((node, index) => (
            <button type="button" role="option" id={`infrastructure-result-${index}`}
              aria-selected={index === active} key={node.id} onClick={() => choose(node)}>
              <span className="infrastructure-result-name">{node.name}</span>
              <small>{NATURES_FR[node.kind] || node.kind} · {node.id}</small>
              <span className="infrastructure-result-arrow" aria-hidden="true">↗</span>
            </button>
          )) : <div className="infrastructure-no-results" role="status">Aucun lieu cartographié trouvé. Essayez un autre nom ou identifiant.</div>}
        </div>
        {!!visibleMatches.length && <p className="infrastructure-search-hint">↑ ↓ pour parcourir · Entrée pour localiser · Échap pour fermer</p>}
      </div>}
    </div>
  );
}
