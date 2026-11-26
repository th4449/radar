import { useEffect, useRef, useState } from "preact/hooks";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { pointOf, type PublicAlert } from "../lib/alerts";
import { href } from "../lib/paths";

// Tiles and style from OpenFreeMap. See docs/services/openfreemap.md for its terms.
const STYLE = "https://tiles.openfreemap.org/styles/positron";

export type Box = [number, number, number, number];
export const STATE_BOX: Record<string, Box> = {
  TX: [-106.65, 25.84, -93.51, 36.5],
  MI: [-90.42, 41.7, -82.41, 48.31],
};
const BOTH: Box = [-106.65, 25.84, -82.41, 48.31];

interface Props {
  alerts: PublicAlert[];
  /** The state to frame when there is no point to frame. */
  state?: string;
  /** Frame the points themselves, for a county or a single alert. */
  close?: boolean;
}

/** The alerts that have a point on record, one ink, on a quiet map. */
export function AlertMap({ alerts, state, close }: Props) {
  const holder = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let map: { remove: () => void } | null = null;
    let gone = false;
    const points = alerts
      .map((alert) => ({ alert, at: pointOf(alert) }))
      .filter((p): p is { alert: PublicAlert; at: [number, number] } => p.at !== null);

    import("maplibre-gl")
      .then(({ Map, NavigationControl, LngLatBounds, setWorkerUrl }) => {
        if (gone || !holder.current) return;
        setWorkerUrl(workerUrl);
        let bounds = new LngLatBounds();
        if (close && points.length) {
          for (const p of points) bounds.extend(p.at);
        } else {
          const box = (state && STATE_BOX[state]) || BOTH;
          bounds = new LngLatBounds([box[0], box[1]], [box[2], box[3]]);
        }
        const made = new Map({
          container: holder.current,
          style: STYLE,
          bounds,
          fitBoundsOptions: { padding: 40, maxZoom: 10 },
          cooperativeGestures: true,
          attributionControl: { compact: false },
        });
        map = made;
        made.addControl(new NavigationControl({ showCompass: false }), "top-right");
        made.on("error", () => setFailed(true));
        made.on("load", () => {
          made.addSource("alerts", {
            type: "geojson",
            data: {
              type: "FeatureCollection",
              features: points.map((p) => ({
                type: "Feature",
                geometry: { type: "Point", coordinates: p.at },
                properties: { id: p.alert.alert_id },
              })),
            },
          });
          made.addLayer({
            id: "alerts",
            type: "circle",
            source: "alerts",
            paint: {
              "circle-radius": 7,
              "circle-color": "#1b1b18",
              "circle-stroke-color": "#fbfaf6",
              "circle-stroke-width": 2,
            },
          });
          made.on("click", "alerts", (event) => {
            const id = event.features?.[0]?.properties?.id;
            if (id) window.location.assign(href(`/alert/?id=${id}`));
          });
          made.on("mouseenter", "alerts", () => {
            made.getCanvas().style.cursor = "pointer";
          });
          made.on("mouseleave", "alerts", () => {
            made.getCanvas().style.cursor = "";
          });
        });
      })
      .catch(() => setFailed(true));

    return () => {
      gone = true;
      map?.remove();
    };
  }, [alerts, state, close]);

  return (
    <figure class="map">
      <div
        ref={holder}
        class="map-canvas"
        role="img"
        aria-label="Map of confirmed alerts. Every alert on it is also in the list on this page."
      />
      {failed && (
        <figcaption class="note">The map did not load. Every alert is listed on this page.</figcaption>
      )}
    </figure>
  );
}
