"use client";

import { LocateFixed, MapPin, Minus, Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ParkingLot } from "@/lib/api";

interface ParkingMapProps {
  lots: ParkingLot[];
  selectedId?: string;
  theme: "light" | "dark";
  onSelect: (lot: ParkingLot) => void;
  onLocate: (coordinates: { latitude: number; longitude: number }) => void;
}

export function ParkingMap({ lots, selectedId, theme, onSelect, onLocate }: ParkingMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("mapbox-gl").Map | null>(null);
  const [mapError, setMapError] = useState("");
  const [fallbackZoom, setFallbackZoom] = useState(1);
  const token = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;

  useEffect(() => {
    if (!token || !containerRef.current) return;
    let cancelled = false;
    let markers: import("mapbox-gl").Marker[] = [];
    void import("mapbox-gl")
      .then((mapbox) => {
        if (cancelled || !containerRef.current) return;
        mapbox.default.accessToken = token;
        const center = lots[0]
          ? [Number(lots[0].longitude), Number(lots[0].latitude)] as [number, number]
          : [77.5946, 12.9716] as [number, number];
        const map = new mapbox.default.Map({
          container: containerRef.current,
          style: `mapbox://styles/mapbox/${theme === "dark" ? "dark" : "light"}-v11`,
          center,
          zoom: 12,
          attributionControl: false,
        });
        mapRef.current = map;
        map.addControl(new mapbox.default.NavigationControl({ showCompass: false }), "top-right");
        markers = lots.map((lot) => {
          const element = document.createElement("button");
          element.type = "button";
          element.className = `map-pin mapbox-pin${lot.id === selectedId ? " active" : ""}`;
          element.textContent = `₹${Number(lot.starting_hourly_rate ?? 0).toFixed(0)}`;
          element.setAttribute("aria-label", `${lot.name}, ₹${lot.starting_hourly_rate ?? 0} per hour`);
          element.addEventListener("click", () => onSelect(lot));
          return new mapbox.default.Marker({ element })
            .setLngLat([Number(lot.longitude), Number(lot.latitude)])
            .addTo(map);
        });
        map.on("error", () => setMapError("Map tiles could not be loaded. Check the Mapbox token and network."));
      })
      .catch(() => setMapError("The interactive map could not be initialized."));
    return () => {
      cancelled = true;
      markers.forEach((marker) => marker.remove());
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [token, lots, selectedId, onSelect, theme]);

  const locate = () => {
    if (!navigator.geolocation) {
      setMapError("Location services are not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const coordinates = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        };
        mapRef.current?.flyTo({
          center: [coordinates.longitude, coordinates.latitude],
          zoom: 14,
          essential: true,
        });
        setMapError("");
        onLocate(coordinates);
      },
      () => setMapError("Location permission was not granted."),
      { timeout: 8000, maximumAge: 60000 },
    );
  };

  const showMapbox = Boolean(token);
  return (
    <section className="panel map-panel" aria-label="Parking locations map">
      <div className="map-canvas" ref={containerRef} />
      {!showMapbox && (
        <div className="map-fallback" style={{ transform: `scale(${fallbackZoom})` }}>
          <span className="map-label" style={{ top: "17%", left: "19%" }}>INDIRANAGAR</span>
          <span className="map-label" style={{ top: "47%", left: "56%" }}>DOMLUR</span>
          <span className="map-label" style={{ top: "75%", left: "22%" }}>KORAMANGALA</span>
          <span className="map-label" style={{ top: "29%", left: "72%" }}>ULSOOR</span>
          <div className="map-water" />
          {lots.slice(0, 8).map((lot, index) => {
            const points = [[28, 34], [48, 23], [67, 41], [38, 61], [76, 67], [54, 78], [19, 76], [83, 25]];
            const point = points[index];
            return point ? (
              <button
                key={lot.id}
                type="button"
                className={`map-pin${lot.id === selectedId ? " active" : ""}`}
                style={{ left: `${point[0]}%`, top: `${point[1]}%` }}
                onClick={() => onSelect(lot)}
              >
                <MapPin size={12} />₹{Number(lot.starting_hourly_rate ?? 0).toFixed(0)}
              </button>
            ) : null;
          })}
        </div>
      )}
      <div className="map-controls">
        <button type="button" aria-label="Center map on my location" onClick={locate}><LocateFixed size={15} /></button>
        {!showMapbox && <><button type="button" aria-label="Zoom in" onClick={() => setFallbackZoom((zoom) => Math.min(1.5, zoom + 0.1))}><Plus size={15} /></button><button type="button" aria-label="Zoom out" onClick={() => setFallbackZoom((zoom) => Math.max(0.8, zoom - 0.1))}><Minus size={15} /></button></>}
      </div>
      {mapError && <div className="map-message" role="status">{mapError}</div>}
      {!token && <div className="map-legend">Map preview · Add a Mapbox public token for live maps</div>}
      {token && <div className="map-legend">Live availability · Tap a marker to view details</div>}
    </section>
  );
}
