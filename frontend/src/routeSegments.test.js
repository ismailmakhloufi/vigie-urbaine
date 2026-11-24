import { test } from "node:test";
import assert from "node:assert/strict";
import { splitRouteAtGaps } from "./routeSegments.js";

test("une mission ne trace pas de ligne entre les deux rives du lac", () => {
  const north = [36.83572, 10.2406];
  const south = [36.77426, 10.22861];
  assert.deepEqual(splitRouteAtGaps([
    [36.83604, 10.24172], north, south, [36.77467, 10.22798],
  ]), [
    [[36.83604, 10.24172], north],
    [south, [36.77467, 10.22798]],
  ]);
});

test("les tronçons proches restent reliés et les points isolés ne forment pas de tracé", () => {
  assert.deepEqual(splitRouteAtGaps([[36.859, 10.242], [36.862, 10.249], [36.85, 10.248]]), [
    [[36.859, 10.242], [36.862, 10.249], [36.85, 10.248]],
  ]);
  assert.deepEqual(splitRouteAtGaps([[36.8, 10.2], [36.9, 10.3]]), []);
});
