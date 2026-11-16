import { useMemo, useRef, useState } from "react";
import { NATURES_FR } from "../libelles.js";
import { searchInfrastructure } from "../infrastructureSearch.js";

export default function InfrastructureSearch({ infrastructure, onChoose }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const container = useRef(null);
  const matches = useMemo(() => searchInfrastructure(infrastructure, query), [infrastructure, query]);

  const choose = (node) => {
    setQuery(`${node.name} (${node.id})`);
    setOpen(false);
    setActive(-1);
    onChoose(node);
  };

  const onKeyDown = (event) => {
    if (event.key === "Escape") { setOpen(false); setActive(-1); return; }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      setActive((index) => event.key === "ArrowDown"
        ? Math.min(index + 1, matches.length - 1) : Math.max(index - 1, 0));
    }
    if (event.key === "Enter" && open && matches.length) {
      event.preventDefault();
      choose(matches[active < 0 ? 0 : active]);
    }
  };

  return (
    <div className="infrastructure-search" ref={container}
      onBlur={(event) => { if (!container.current?.contains(event.relatedTarget)) setOpen(false); }}>
      <label htmlFor="infrastructure-search-input">Rechercher sur la carte</label>
      <input id="infrastructure-search-input" role="combobox" type="search"
        autoComplete="off" aria-autocomplete="list" aria-expanded={open && !!query.trim()}
        aria-controls="infrastructure-search-results"
        aria-activedescendant={open && active >= 0 ? `infrastructure-result-${active}` : undefined}
        placeholder="Poste électrique, antenne, rue, identifiant…"
        value={query} onFocus={() => setOpen(true)} onKeyDown={onKeyDown}
        onChange={(event) => { setQuery(event.target.value); setActive(-1); setOpen(true); }} />
      {open && query.trim() && <div id="infrastructure-search-results" className="infrastructure-results" role="listbox">
        {matches.length ? matches.map((node, index) => (
          <button type="button" role="option" id={`infrastructure-result-${index}`}
            aria-selected={index === active} key={node.id} onClick={() => choose(node)}>
            <span>{node.name}</span><small>{NATURES_FR[node.kind] || node.kind} · {node.id}</small>
          </button>
        )) : <div className="infrastructure-no-results">Aucun lieu cartographié trouvé.</div>}
      </div>}
    </div>
  );
}
