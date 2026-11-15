import { test } from "node:test";
import { strict as assert } from "node:assert";
import { escapeHtml } from "./escapeHtml.js";

test("les textes non fiables restent du texte dans les popups Leaflet", () => {
  assert.equal(escapeHtml('<img src=x onerror="alert(1)">'),
    '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
  assert.equal(escapeHtml("Hôpital d'Ariana & alentours"),
    "Hôpital d&#39;Ariana &amp; alentours");
  assert.equal(escapeHtml(null), "");
});
