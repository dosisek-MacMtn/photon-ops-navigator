"use client";

import type { Feature, FeatureCollection, LineString, Point } from "geojson";
import maplibregl, { GeoJSONSource, LngLatBounds, Map, Popup } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";

import type { CircuitPath, Correlation, DemoOverview } from "@/types/network";

type LayerVisibility = {
  satellite: boolean;
  backbone: boolean;
  distribution: boolean;
  drops: boolean;
  assets: boolean;
};

type Props = {
  overview?: DemoOverview;
  path?: CircuitPath;
  correlation?: Correlation;
  layers: LayerVisibility;
};

const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };

export function MapView({ overview, path, correlation, layers }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      center: [-69.289, 45.023],
      zoom: 11.7,
      attributionControl: false,
      style: {
        version: 8,
        sources: {
          "esri-world-imagery": {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            maxzoom: 19,
            attribution: "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
          },
          "esri-reference-labels": {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            maxzoom: 19,
          },
        },
        layers: [
          { id: "background", type: "background", paint: { "background-color": "#07111c" } },
          {
            id: "satellite-imagery",
            type: "raster",
            source: "esri-world-imagery",
            paint: {
              "raster-opacity": 0.82,
              "raster-saturation": -0.25,
              "raster-contrast": 0.16,
              "raster-brightness-max": 0.72,
            },
          },
          {
            id: "satellite-labels",
            type: "raster",
            source: "esri-reference-labels",
            paint: { "raster-opacity": 0.72 },
          },
        ],
      },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => {
      map.addSource("network-cables", { type: "geojson", data: EMPTY });
      map.addSource("network-assets", { type: "geojson", data: EMPTY });
      map.addSource("selected-path", { type: "geojson", data: EMPTY });
      map.addSource("fault-point", { type: "geojson", data: EMPTY });

      map.addLayer({
        id: "cable-backbone",
        type: "line",
        source: "network-cables",
        filter: ["==", ["get", "cable_type"], "backbone"],
        paint: { "line-color": "#3bd7ff", "line-width": 3.2, "line-opacity": 0.9 },
      });
      map.addLayer({
        id: "cable-distribution",
        type: "line",
        source: "network-cables",
        filter: ["==", ["get", "cable_type"], "distribution"],
        paint: { "line-color": "#79a8bd", "line-width": 1.8, "line-opacity": 0.88 },
      });
      map.addLayer({
        id: "cable-drops",
        type: "line",
        source: "network-cables",
        filter: ["==", ["get", "cable_type"], "service_drop"],
        paint: { "line-color": "#1b3545", "line-width": 1, "line-opacity": 0.55 },
      });
      map.addLayer({
        id: "path-glow",
        type: "line",
        source: "selected-path",
        paint: { "line-color": "#2fc3e8", "line-width": 11, "line-opacity": 0.12, "line-blur": 5 },
      });
      map.addLayer({
        id: "path-core",
        type: "line",
        source: "selected-path",
        paint: { "line-color": "#63d8f3", "line-width": 4, "line-opacity": 1 },
      });
      map.addLayer({
        id: "network-assets-layer",
        type: "circle",
        source: "network-assets",
        paint: {
          "circle-radius": ["match", ["get", "asset_type"], "pop", 8, "lcp", 6.5, "cabinet", 6, "splice_closure", 5, "pole", 2.5, 1.8],
          "circle-color": [
            "match",
            ["get", "asset_type"],
            "pop", "#f2a93b",
            "lcp", "#a9e1e7",
            "cabinet", "#d8e6ec",
            "splice_closure", "#2fc3e8",
            "pole", "#66889a",
            "#b0c5cf",
          ],
          "circle-stroke-color": "#07111c",
          "circle-stroke-width": 1.4,
          "circle-opacity": ["match", ["get", "asset_type"], "service_location", 0.5, 1],
        },
      });
      map.addLayer({
        id: "fault-halo",
        type: "circle",
        source: "fault-point",
        paint: { "circle-radius": 22, "circle-color": "#f45b69", "circle-opacity": 0.16, "circle-blur": 0.3 },
      });
      map.addLayer({
        id: "fault-core",
        type: "circle",
        source: "fault-point",
        paint: { "circle-radius": 6, "circle-color": "#f7d56d", "circle-stroke-color": "#f45b69", "circle-stroke-width": 3 },
      });

      map.on("click", "network-assets-layer", (event) => {
        const feature = event.features?.[0];
        if (!feature || feature.geometry.type !== "Point") return;
        const [longitude, latitude] = feature.geometry.coordinates as [number, number];
        const popupContent = document.createElement("div");
        const popupTitle = document.createElement("strong");
        const popupType = document.createElement("span");
        popupTitle.textContent = String(feature.properties?.name ?? "Mapped asset");
        popupType.textContent = String(feature.properties?.asset_type ?? "asset").replaceAll("_", " ");
        popupContent.append(popupTitle, popupType);
        new Popup({ closeButton: false, offset: 10 })
          .setLngLat([longitude, latitude])
          .setDOMContent(popupContent)
          .addTo(map);
      });
      map.on("mouseenter", "network-assets-layer", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "network-assets-layer", () => (map.getCanvas().style.cursor = ""));
      setReady(true);
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !overview) return;
    const cableFeatures: Feature<LineString>[] = overview.cables.map((cable) => ({
      type: "Feature",
      properties: { id: cable.id, name: cable.name, cable_type: cable.cable_type },
      geometry: { type: "LineString", coordinates: cable.coordinates },
    }));
    const assetFeatures: Feature<Point>[] = overview.assets.map((asset) => ({
      type: "Feature",
      properties: { id: asset.id, name: asset.name, asset_type: asset.asset_type },
      geometry: { type: "Point", coordinates: [asset.longitude, asset.latitude] },
    }));
    (map.getSource("network-cables") as GeoJSONSource).setData({ type: "FeatureCollection", features: cableFeatures });
    (map.getSource("network-assets") as GeoJSONSource).setData({ type: "FeatureCollection", features: assetFeatures });
  }, [overview, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const pathFeatures: Feature<LineString>[] =
      path?.service_leg_segments.map((segment) => ({
        type: "Feature",
        properties: { cable_id: segment.cable_id, sequence: segment.sequence },
        geometry: { type: "LineString", coordinates: segment.coordinates },
      })) ?? [];
    (map.getSource("selected-path") as GeoJSONSource).setData({ type: "FeatureCollection", features: pathFeatures });
    if (pathFeatures.length) {
      const bounds = new LngLatBounds();
      pathFeatures.forEach((feature) => feature.geometry.coordinates.forEach((coordinate) => bounds.extend(coordinate as [number, number])));
      map.fitBounds(bounds, { padding: 72, duration: 850, maxZoom: 14.5 });
    }
  }, [path, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const features: Feature<Point>[] = correlation
      ? [
          {
            type: "Feature",
            properties: { confidence: correlation.confidence },
            geometry: {
              type: "Point",
              coordinates: [
                correlation.recommended_field_search_area.longitude,
                correlation.recommended_field_search_area.latitude,
              ],
            },
          },
        ]
      : [];
    (map.getSource("fault-point") as GeoJSONSource).setData({ type: "FeatureCollection", features });
  }, [correlation, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const visibility = (visible: boolean) => (visible ? "visible" : "none");
    map.setLayoutProperty("satellite-imagery", "visibility", visibility(layers.satellite));
    map.setLayoutProperty("satellite-labels", "visibility", visibility(layers.satellite));
    map.setLayoutProperty("cable-backbone", "visibility", visibility(layers.backbone));
    map.setLayoutProperty("cable-distribution", "visibility", visibility(layers.distribution));
    map.setLayoutProperty("cable-drops", "visibility", visibility(layers.drops));
    map.setLayoutProperty("network-assets-layer", "visibility", visibility(layers.assets));
  }, [layers, ready]);

  return (
    <>
      <div ref={containerRef} className="map-canvas" aria-label="Fiber network operations map" />
      <a
        className="map-attribution"
        href="https://www.esri.com/en-us/legal/terms/full-master-agreement"
        target="_blank"
        rel="noreferrer"
      >
        Imagery © Esri, Maxar, Earthstar Geographics, GIS User Community
      </a>
    </>
  );
}
