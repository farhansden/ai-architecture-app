/**
 * PascalViewer.tsx  —  Pascal Editor 3D view integration
 * ========================================================
 *
 * Drop this component anywhere in your frontend after a floor plan has
 * been generated. It:
 *   1. Accepts the `per_floor_layouts` + `parsed` data from your API response
 *   2. Converts them to Pascal scene JSON (client-side, via a POST to /api/pascal/from-layout)
 *   3. Opens Pascal Editor pre-loaded with the scene — either in an iframe
 *      or in a new tab
 *
 * Usage:
 *   <PascalViewer
 *     perFloorLayouts={result.per_floor_layouts}
 *     parsed={result.parsed_data}
 *     projectName="3BHK Mysuru House"
 *   />
 *
 * Props:
 *   perFloorLayouts   The per_floor_layouts dict from your API response
 *   parsed            The parsed_json from llm_parser
 *   projectName       Display name
 *   mode              "iframe" (embedded) | "tab" (opens new tab) | "panel" (side panel)
 *   height            iframe height (default: 600px)
 *   onSceneReady      callback(sceneJson) — called when Pascal scene is ready
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { getApiBase } from "@/lib/apiBase";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Room {
  name: string;
  floor: number;
  x: number;
  y: number;
  width: number;
  height: number;
  width_ft: number;
  depth_ft: number;
  area_sqft: number;
  __vastu_zone?: string;
  __cat?: string;
  __is_carved?: boolean;
  windows?: number;
  door_count?: number;
  notes?: string;
}

interface FloorLayout {
  rooms: Room[];
  built_up_x: number;
  built_up_y: number;
  built_up_w: number;
  built_up_h: number;
  plot_w_px: number;
  plot_h_px: number;
  facing?: string;
  warnings?: string[];
  failed_rooms?: string[];
}

interface ParsedJSON {
  bhk_type?: string;
  plot_width_ft?: number;
  plot_depth_ft?: number;
  style?: string;
  floors?: number;
  vastu_compliant?: boolean;
  plot_facing?: string;
  budget?: number;
  [key: string]: unknown;
}

interface PascalViewerProps {
  perFloorLayouts: Record<string, FloorLayout>;
  parsed: ParsedJSON;
  projectName?: string;
  apiBase?: string;
  mode?: "iframe" | "tab" | "panel";
  height?: number | string;
  onSceneReady?: (scene: Record<string, unknown>) => void;
  className?: string;
}

interface ConvertResult {
  job_id: string;
  scene_json: Record<string, unknown>;
  node_count: number;
  viewer_url: string;
  scene_url: string;
}

// ─── Room color map (matches pascal_scene_converter.py) ──────────────────────

const ROOM_COLORS: Record<string, string> = {
  living_room: "#FDF6E3",
  dining_room: "#FDF6E3",
  master_bedroom: "#E8EEF8",
  bedroom: "#E8EEF8",
  kitchen: "#E8F5EC",
  bathroom: "#E0F2F8",
  common_bathroom: "#E0F2F8",
  corridor: "#F5F5EE",
  foyer: "#FDF0DC",
  pooja_room: "#FDF0DC",
  sit_out: "#E8F2E8",
  car_porch: "#EEEBD8",
  terrace: "#E8F2E8",
  default: "#FAFAFA",
};

const ROOM_LABELS: Record<string, string> = {
  living_room: "Living Room",
  dining_room: "Dining Room",
  master_bedroom: "Master Bedroom",
  parents_bedroom: "Parents Bedroom",
  bedroom: "Bedroom",
  kitchen: "Kitchen",
  dry_kitchen: "Dry Kitchen",
  bathroom: "Bathroom",
  common_bathroom: "Common Bath",
  corridor: "Corridor",
  foyer: "Foyer",
  pooja_room: "Prayer Room",
  sit_out: "Sit-out",
  car_porch: "Car Porch",
  terrace: "Terrace",
  staircase: "Staircase",
  utility_room: "Utility",
  store_room: "Store Room",
  home_office: "Home Office",
  family_lounge: "Family Lounge",
  servant_quarters: "Servant Qtrs",
  walk_in_wardrobe: "Wardrobe",
};

function getRoomLabel(room: Room): string {
  const cat = room.__cat || "";
  return ROOM_LABELS[cat] || room.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Main Component ───────────────────────────────────────────────────────────

function pascalSceneFromResponse(data: Record<string, unknown>): ConvertResult {
  const scene_json = (data.scene_json ?? data) as Record<string, unknown>;
  const nodes = (scene_json.nodes ?? {}) as Record<string, unknown>;
  return {
    job_id: String(data.job_id ?? ""),
    scene_json,
    node_count: Object.keys(nodes).length,
    viewer_url: String(data.viewer_url ?? ""),
    scene_url: String(data.scene_url ?? ""),
  };
}

export function PascalViewer({
  perFloorLayouts,
  parsed,
  projectName = "Floor Plan",
  apiBase = getApiBase(),
  mode = "iframe",
  height = 600,
  onSceneReady,
  className = "",
}: PascalViewerProps) {
  const api = apiBase.trim().replace(/\/+$/, "");
  const [status, setStatus] = useState<"idle" | "converting" | "ready" | "error">("idle");
  const [result, setResult] = useState<ConvertResult | null>(null);
  const [error, setError] = useState<string>("");
  const [activeFloor, setActiveFloor] = useState<string>("0");
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const floorCount = Object.keys(perFloorLayouts).length;
  const floorLabels: Record<string, string> = {
    "0": "Ground Floor",
    "1": "First Floor",
    "2": "Second Floor",
    "3": "Third Floor",
  };

  // ── Convert layout → Pascal scene via API ──────────────────────────────────
  const convertToPascal = useCallback(async () => {
    setStatus("converting");
    setError("");

    try {
      const resp = await fetch(`${api}/api/pascal/scene/multi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          per_floor_layouts: perFloorLayouts,
          parsed,
          project_name: projectName,
        }),
      });

      if (!resp.ok) {
        const err = await resp.text();
        throw new Error(`API error ${resp.status}: ${err}`);
      }

      const data = pascalSceneFromResponse(await resp.json());
      setResult(data);
      setStatus("ready");
      onSceneReady?.(data.scene_json);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  }, [api, perFloorLayouts, parsed, projectName, onSceneReady]);

  // ── Open in Pascal Editor (new tab) ───────────────────────────────────────
  const openInPascal = useCallback(() => {
    if (!result) return;
    const sceneStr = JSON.stringify(result.scene_json);
    const b64 = btoa(unescape(encodeURIComponent(sceneStr)))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
    window.open(`https://editor.pascal.app?importScene=${b64}`, "_blank");
  }, [result]);

  // ── Download Pascal scene JSON ─────────────────────────────────────────────
  const downloadScene = useCallback(() => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result.scene_json, null, 2)], {
      type: "application/json",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${projectName.replace(/\s+/g, "_")}_pascal_scene.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }, [result, projectName]);

  // ── Room summary for current floor ────────────────────────────────────────
  const currentFloorRooms = (perFloorLayouts[activeFloor]?.rooms || []).filter(
    (r) => !r.__is_carved
  );

  // ─── Render: idle state ───────────────────────────────────────────────────
  if (status === "idle") {
    return (
      <div className={`pascal-viewer pascal-idle ${className}`} style={styles.container}>
        {/* Room preview grid */}
        <div style={styles.previewSection}>
          <div style={styles.sectionTitle}>Floor Plan Summary</div>

          {/* Floor tabs */}
          {floorCount > 1 && (
            <div style={styles.floorTabs}>
              {Object.keys(perFloorLayouts).map((fi) => (
                <button
                  key={fi}
                  style={{
                    ...styles.floorTab,
                    ...(activeFloor === fi ? styles.floorTabActive : {}),
                  }}
                  onClick={() => setActiveFloor(fi)}
                >
                  {floorLabels[fi] || `Floor ${fi}`}
                </button>
              ))}
            </div>
          )}

          {/* Room chips */}
          <div style={styles.roomGrid}>
            {currentFloorRooms.map((room) => {
              const cat = room.__cat || "default";
              const color = ROOM_COLORS[cat] || ROOM_COLORS.default;
              return (
                <div
                  key={room.name}
                  style={{ ...styles.roomChip, borderLeftColor: color }}
                >
                  <div style={{ ...styles.roomDot, background: color }} />
                  <div style={styles.roomChipContent}>
                    <div style={styles.roomChipName}>{getRoomLabel(room)}</div>
                    <div style={styles.roomChipDims}>
                      {room.width_ft?.toFixed(0)}′ × {room.depth_ft?.toFixed(0)}′ &nbsp;·&nbsp;
                      {room.area_sqft?.toFixed(0)} sqft
                    </div>
                  </div>
                  {room.__vastu_zone && (
                    <div style={styles.vasteBadge}>{room.__vastu_zone}</div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Stats */}
          <div style={styles.statsRow}>
            <div style={styles.stat}>
              <div style={styles.statValue}>{currentFloorRooms.length}</div>
              <div style={styles.statLabel}>Rooms</div>
            </div>
            <div style={styles.stat}>
              <div style={styles.statValue}>{floorCount}</div>
              <div style={styles.statLabel}>Floors</div>
            </div>
            <div style={styles.stat}>
              <div style={styles.statValue}>
                {parsed.plot_width_ft}×{parsed.plot_depth_ft}
              </div>
              <div style={styles.statLabel}>Plot (ft)</div>
            </div>
            <div style={styles.stat}>
              <div style={styles.statValue}>
                {parsed.vastu_compliant ? "✓" : "—"}
              </div>
              <div style={styles.statLabel}>Vastu</div>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div style={styles.ctaSection}>
          <div style={styles.ctaTitle}>View in 3D</div>
          <div style={styles.ctaDesc}>
            Open your floor plan in Pascal Editor — a professional 3D architectural
            viewer with walls, slabs, zones, doors, and windows.
          </div>
          <div style={styles.ctaButtons}>
            <button style={styles.btnPrimary} onClick={convertToPascal}>
              Launch 3D View
            </button>
            <button
              style={styles.btnSecondary}
              onClick={() =>
                window.open("https://editor.pascal.app", "_blank")
              }
            >
              Open Pascal Editor ↗
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─── Render: converting ───────────────────────────────────────────────────
  if (status === "converting") {
    return (
      <div style={{ ...styles.container, ...styles.centered }}>
        <div style={styles.spinner} />
        <div style={styles.loadTitle}>Generating 3D Scene…</div>
        <div style={styles.loadSub}>
          Converting {Object.values(perFloorLayouts).reduce(
            (acc, fl) => acc + (fl.rooms?.length || 0),
            0
          )} rooms across {floorCount} floor{floorCount > 1 ? "s" : ""} into Pascal format
        </div>
      </div>
    );
  }

  // ─── Render: error ────────────────────────────────────────────────────────
  if (status === "error") {
    return (
      <div style={{ ...styles.container, ...styles.centered }}>
        <div style={styles.errorIcon}>⚠</div>
        <div style={styles.loadTitle}>Conversion Failed</div>
        <div style={styles.loadSub}>{error}</div>
        <button style={styles.btnPrimary} onClick={convertToPascal}>
          Retry
        </button>
      </div>
    );
  }

  // ─── Render: ready ────────────────────────────────────────────────────────
  if (!result) return null;

  return (
    <div className={`pascal-viewer pascal-ready ${className}`} style={styles.container}>
      {/* Toolbar */}
      <div style={styles.toolbar}>
        <div style={styles.toolbarTitle}>
          <span style={styles.toolbarLogo}>Pascal 3D</span>
          <span style={styles.toolbarBadge}>{projectName}</span>
          <span style={styles.toolbarStats}>
            {result.node_count} nodes · {floorCount} floor{floorCount > 1 ? "s" : ""}
          </span>
        </div>
        <div style={styles.toolbarButtons}>
          <button style={styles.btnSm} onClick={downloadScene}>
            ↓ Scene JSON
          </button>
          <button style={styles.btnSmPrimary} onClick={openInPascal}>
            Open in Pascal ↗
          </button>
        </div>
      </div>

      {/* Pascal Editor iframe */}
      {mode === "iframe" ? (
        <iframe
          ref={iframeRef}
          src={
            result.viewer_url ||
            (result.job_id ? `${api}/api/pascal/viewer/${result.job_id}` : undefined)
          }
          style={{ ...styles.iframe, height }}
          title="Pascal 3D Editor"
          allow="cross-origin-isolated"
        />
      ) : (
        /* Panel mode — show scene info + open button */
        <div style={styles.panelReady}>
          <div style={styles.panelIcon}>🏠</div>
          <div style={styles.panelTitle}>3D Scene Ready</div>
          <div style={styles.panelDesc}>
            {result.node_count} Pascal nodes generated across {floorCount} level
            {floorCount > 1 ? "s" : ""}. Open in Pascal Editor for the full
            interactive 3D experience with walls, zones, orbit controls, and
            exploded view.
          </div>
          <button style={styles.btnPrimary} onClick={openInPascal}>
            Open in Pascal Editor ↗
          </button>
          <button style={styles.btnSecondary} onClick={downloadScene}>
            Download Scene JSON
          </button>
          <div style={styles.panelNote}>
            Tip: In Pascal Editor, use{" "}
            <strong>File → Import Scene</strong> if the URL param does not work.
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Quick launch button (minimal, for embedding next to SVG viewer) ─────────

export function PascalLaunchButton({
  perFloorLayouts,
  parsed,
  projectName = "Floor Plan",
  apiBase = getApiBase(),
}: Pick<PascalViewerProps, "perFloorLayouts" | "parsed" | "projectName" | "apiBase">) {
  const [loading, setLoading] = useState(false);
  const api = apiBase.trim().replace(/\/+$/, "");

  const launch = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${api}/api/pascal/scene/multi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          per_floor_layouts: perFloorLayouts,
          parsed,
          project_name: projectName,
        }),
      });
      const data = pascalSceneFromResponse(await resp.json());
      if (data.scene_json) {
        const sceneStr = JSON.stringify(data.scene_json);
        const b64 = btoa(unescape(encodeURIComponent(sceneStr)))
          .replace(/\+/g, "-")
          .replace(/\//g, "_")
          .replace(/=+$/, "");
        window.open(`https://editor.pascal.app?importScene=${b64}`, "_blank");
      }
    } catch (e) {
      console.error("Pascal launch failed:", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={launch}
      disabled={loading}
      style={{
        padding: "10px 22px",
        background: loading ? "#8a8070" : "#c8a96e",
        color: "#1a1714",
        border: "none",
        borderRadius: "6px",
        fontWeight: 600,
        fontSize: "13px",
        cursor: loading ? "not-allowed" : "pointer",
        display: "flex",
        alignItems: "center",
        gap: "8px",
        transition: "all 0.15s",
      }}
    >
      {loading ? (
        <>
          <span
            style={{
              width: 14,
              height: 14,
              border: "2px solid rgba(26,23,20,0.3)",
              borderTopColor: "#1a1714",
              borderRadius: "50%",
              display: "inline-block",
              animation: "spin 0.7s linear infinite",
            }}
          />
          Converting…
        </>
      ) : (
        <>🏗 View in 3D (Pascal)</>
      )}
    </button>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: "'DM Mono', 'Courier New', monospace",
    background: "#1a1714",
    borderRadius: "8px",
    overflow: "hidden",
    color: "#f4f0e8",
  },
  centered: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: "16px",
    padding: "60px 32px",
    minHeight: "300px",
    textAlign: "center",
  },
  previewSection: {
    padding: "20px 24px 16px",
    borderBottom: "1px solid rgba(200,169,110,0.15)",
  },
  sectionTitle: {
    fontSize: "11px",
    fontWeight: 500,
    letterSpacing: "0.12em",
    textTransform: "uppercase" as const,
    color: "#8a8070",
    marginBottom: "14px",
  },
  floorTabs: {
    display: "flex",
    gap: "6px",
    marginBottom: "14px",
  },
  floorTab: {
    padding: "5px 12px",
    border: "1px solid rgba(200,169,110,0.25)",
    borderRadius: "4px",
    background: "transparent",
    color: "#8a8070",
    fontSize: "11px",
    cursor: "pointer",
    fontFamily: "inherit",
    transition: "all 0.12s",
  },
  floorTabActive: {
    background: "rgba(200,169,110,0.15)",
    borderColor: "#c8a96e",
    color: "#c8a96e",
  },
  roomGrid: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "5px",
    maxHeight: "280px",
    overflowY: "auto" as const,
  },
  roomChip: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "6px 10px",
    background: "rgba(255,255,255,0.04)",
    borderRadius: "4px",
    borderLeft: "3px solid #888",
  },
  roomDot: {
    width: "8px",
    height: "8px",
    borderRadius: "2px",
    flexShrink: 0,
  },
  roomChipContent: {
    flex: 1,
    minWidth: 0,
  },
  roomChipName: {
    fontSize: "12px",
    fontWeight: 500,
    color: "#f4f0e8",
  },
  roomChipDims: {
    fontSize: "10px",
    color: "#8a8070",
    marginTop: "1px",
  },
  vasteBadge: {
    padding: "2px 6px",
    background: "rgba(200,169,110,0.12)",
    border: "1px solid rgba(200,169,110,0.2)",
    borderRadius: "3px",
    fontSize: "9px",
    color: "#c8a96e",
    flexShrink: 0,
  },
  statsRow: {
    display: "flex",
    gap: "0",
    marginTop: "14px",
    borderTop: "1px solid rgba(200,169,110,0.1)",
    paddingTop: "12px",
  },
  stat: {
    flex: 1,
    textAlign: "center" as const,
  },
  statValue: {
    fontSize: "18px",
    fontWeight: 500,
    color: "#c8a96e",
    fontFamily: "'Georgia', serif",
  },
  statLabel: {
    fontSize: "9px",
    color: "#8a8070",
    letterSpacing: "0.08em",
    textTransform: "uppercase" as const,
    marginTop: "2px",
  },
  ctaSection: {
    padding: "20px 24px 24px",
  },
  ctaTitle: {
    fontFamily: "'Georgia', serif",
    fontSize: "18px",
    fontWeight: 300,
    color: "#c8a96e",
    marginBottom: "8px",
  },
  ctaDesc: {
    fontSize: "11px",
    color: "#8a8070",
    lineHeight: "1.6",
    marginBottom: "16px",
  },
  ctaButtons: {
    display: "flex",
    gap: "10px",
    flexWrap: "wrap" as const,
  },
  btnPrimary: {
    padding: "10px 22px",
    background: "#c8a96e",
    color: "#1a1714",
    border: "none",
    borderRadius: "5px",
    fontWeight: 600,
    fontSize: "13px",
    cursor: "pointer",
    fontFamily: "inherit",
  },
  btnSecondary: {
    padding: "10px 22px",
    background: "transparent",
    color: "#c8a96e",
    border: "1px solid rgba(200,169,110,0.4)",
    borderRadius: "5px",
    fontWeight: 400,
    fontSize: "13px",
    cursor: "pointer",
    fontFamily: "inherit",
  },
  spinner: {
    width: "36px",
    height: "36px",
    border: "3px solid rgba(200,169,110,0.2)",
    borderTopColor: "#c8a96e",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  loadTitle: {
    fontFamily: "'Georgia', serif",
    fontSize: "20px",
    color: "#c8a96e",
  },
  loadSub: {
    fontSize: "12px",
    color: "#8a8070",
    maxWidth: "320px",
  },
  errorIcon: {
    fontSize: "32px",
    color: "#e86c4a",
  },
  toolbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 16px",
    background: "rgba(26,23,20,0.95)",
    borderBottom: "1px solid rgba(200,169,110,0.15)",
  },
  toolbarTitle: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  toolbarLogo: {
    fontFamily: "'Georgia', serif",
    fontSize: "15px",
    color: "#c8a96e",
    letterSpacing: "0.06em",
  },
  toolbarBadge: {
    padding: "2px 8px",
    background: "rgba(200,169,110,0.12)",
    border: "1px solid rgba(200,169,110,0.25)",
    borderRadius: "10px",
    fontSize: "11px",
    color: "#c8a96e",
  },
  toolbarStats: {
    fontSize: "10px",
    color: "#8a8070",
  },
  toolbarButtons: {
    display: "flex",
    gap: "8px",
  },
  btnSm: {
    padding: "5px 12px",
    background: "transparent",
    border: "1px solid rgba(200,169,110,0.3)",
    color: "#c8a96e",
    borderRadius: "4px",
    fontSize: "11px",
    cursor: "pointer",
    fontFamily: "inherit",
  },
  btnSmPrimary: {
    padding: "5px 12px",
    background: "#c8a96e",
    border: "1px solid #c8a96e",
    color: "#1a1714",
    borderRadius: "4px",
    fontSize: "11px",
    cursor: "pointer",
    fontFamily: "inherit",
    fontWeight: 600,
  },
  iframe: {
    width: "100%",
    border: "none",
    display: "block",
    minHeight: "400px",
  },
  panelReady: {
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    textAlign: "center" as const,
    padding: "40px 32px",
    gap: "14px",
  },
  panelIcon: {
    fontSize: "40px",
  },
  panelTitle: {
    fontFamily: "'Georgia', serif",
    fontSize: "22px",
    color: "#c8a96e",
  },
  panelDesc: {
    fontSize: "12px",
    color: "#8a8070",
    lineHeight: "1.7",
    maxWidth: "380px",
  },
  panelNote: {
    fontSize: "10px",
    color: "#5a5448",
    maxWidth: "340px",
    lineHeight: "1.6",
    marginTop: "4px",
  },
};

export default PascalViewer;