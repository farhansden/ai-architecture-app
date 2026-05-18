"use client";

import { useState, useRef, useEffect, useMemo, type ReactNode } from "react";

import { LayoutEditorPhaseA } from "@/components/LayoutEditorPhaseA";

// ── Inject @keyframes spin once ───────────────────────────────────────────────
// Inline style objects can't define @keyframes, so we inject once into <head>.
if (typeof document !== "undefined") {
  const ID = "__pascal_spin_kf__";
  if (!document.getElementById(ID)) {
    const s = document.createElement("style");
    s.id = ID;
    s.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
    document.head.appendChild(s);
  }
}

// ── API contract ───────────────────────────────────────────────────────────────

export interface GenerateApiResult {
  // PRIMARY: SVG floor plans keyed by floor index "0", "1", ...
  floors:              Record<string, string>;
  layout_data:         Record<string, unknown>;
  design_reasoning:    string;
  validation:          string;
  project_data:        Record<string, unknown>;
  dxf_paths?:          Record<string, string>;

  /** Maket-style narrative bundle from structured parser (also inside project_data). */
  maket_deliverable?: Record<string, string>;

  // 3D HTML viewers keyed by floor index "0", "1", ...
  floors_3d?:          Record<string, string>;
  ground_floor_3d?:    string;
  renderer_3d_used?:   boolean;

  // Scores
  scores?:             Record<string, FloorScore>;
  ground_score?:       FloorScore;
  scorer_used?:        boolean;

  // Stats
  floors_generated:    number;
  rooms_placed:        number;
  rooms_failed:        string[];
  warnings:            string[];

  // Legacy fallbacks
  per_floor_svgs?:     Record<string, string>;
  per_floor_3d?:       Record<string, string>;
  ground_floor_svg?:   string;
}

export interface FloorScore {
  total:      number;
  grade:      string;
  breakdown:  Record<string, number>;
  issues?:    string[];
  strengths?: string[];
}

export interface ResultPanelProps {
  result:     GenerateApiResult | null | undefined;
  isLoading?: boolean;
  error?:     string | null;
  apiBase?:   string;
}

export type VisualFloorPlanApiResult = GenerateApiResult;

// ── Helpers ───────────────────────────────────────────────────────────────────

const FLOOR_LABELS: Record<string, string> = {
  "0": "GROUND FLOOR", "1": "FIRST FLOOR",
  "2": "SECOND FLOOR", "3": "THIRD FLOOR",
};

function floorSlug(key: string) {
  return ({ "0": "ground", "1": "first", "2": "second", "3": "third" } as Record<string, string>)[key]
    ?? `floor_${key}`;
}

function downloadSvg(svgStr: string, filename: string) {
  const blob = new Blob([svgStr], { type: "image/svg+xml" });
  const url  = URL.createObjectURL(blob);
  Object.assign(document.createElement("a"), { href: url, download: filename }).click();
  URL.revokeObjectURL(url);
}

// ── Shared sub-components ─────────────────────────────────────────────────────

function LoadingState() {
  return (
    <div style={styles.card}>
      <div style={styles.loadingInner}>
        <div style={styles.spinner} />
        <div>
          <p style={styles.loadingTitle}>Generating floor plan…</p>
          <p style={styles.loadingSubtitle}>
            Call 1: Reasoning → Call 2: JSON + Maket narrative → Call 3: Validation → layout → SVG → 3D
          </p>
        </div>
      </div>
    </div>
  );
}

function ErrorState({ error }: { error: string }) {
  return (
    <div style={{ ...styles.card, border: "1px solid #d4a0a0" }}>
      <p style={styles.sectionLabel}>Error</p>
      <p style={{ color: "#7a3535", fontSize: 14, marginTop: 6 }}>{error}</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div style={{ ...styles.card, textAlign: "center", padding: "48px 24px" }}>
      <svg width="40" height="40" viewBox="0 0 40 40" fill="none"
        style={{ margin: "0 auto 12px", display: "block" }}>
        <rect x="4" y="4" width="32" height="32" rx="4"
          stroke="#C8BFB0" strokeWidth="1.5" fill="none" />
        <path d="M13 20h14M13 26h8" stroke="#C8BFB0" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M13 14h14" stroke="#5A6B4A" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <p style={{ ...styles.sectionLabel, marginBottom: 6 }}>No floor plan yet</p>
      <p style={styles.emptyText}>Enter your design brief above and click Generate Design</p>
    </div>
  );
}

function SvgUpload3DCard({ apiBase }: { apiBase: string }) {
  const [svgFile, setSvgFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [svg3dHtml, setSvg3dHtml] = useState<string>("");
  const [includeAiRenders, setIncludeAiRenders] = useState(false);

  async function handleUpload() {
    if (!svgFile) return;
    setIsUploading(true);
    setUploadError(null);
    setSvg3dHtml("");
    try {
      const form = new FormData();
      form.append("file", svgFile);
      form.append("style", "modern");
      form.append("plot_facing", "north");
      form.append("vastu_compliant", "false");
      form.append("include_ai_renders", includeAiRenders ? "true" : "false");

      const res = await fetch(`${apiBase}/3d/from-svg/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const text = await res.text();
        let detail = text;
        try { detail = JSON.parse(text)?.detail ?? text; } catch {}
        throw new Error(detail || `Upload failed (${res.status})`);
      }

      const data = await res.json() as { html?: string };
      if (!data?.html || typeof data.html !== "string") {
        throw new Error("Backend did not return 3D HTML");
      }
      setSvg3dHtml(data.html);
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "SVG upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div style={styles.floorCard}>
      <div style={styles.floorCardHeader}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ ...styles.floorBadge, background: "#1a1714", color: "#c8a96e", border: "1px solid #3a3028" }}>
            SVG → 3D
          </div>
          <span style={{ fontSize: 10, color: C.inkLight, letterSpacing: "0.06em", textTransform: "uppercase" as const }}>
            Upload SVG · Generate Interactive 3D
          </span>
        </div>
      </div>

      <div style={{ padding: 16, borderBottom: `1px solid ${C.border}` }}>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <input
            type="file"
            accept=".svg,image/svg+xml"
            onChange={(e) => setSvgFile(e.target.files?.[0] ?? null)}
            style={{ fontSize: 12 }}
          />
          <label style={{ fontSize: 12, color: C.inkMid, display: "flex", gap: 6, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={includeAiRenders}
              onChange={(e) => setIncludeAiRenders(e.target.checked)}
            />
            also generate AI exterior/interior renders
          </label>
          <button
            style={styles.downloadBtn}
            onClick={handleUpload}
            disabled={!svgFile || isUploading}
          >
            {isUploading ? "Generating..." : "Upload & Generate 3D"}
          </button>
        </div>
        {svgFile && (
          <p style={{ margin: "8px 0 0", fontSize: 12, color: C.inkLight }}>
            Selected: {svgFile.name}
          </p>
        )}
        {uploadError && (
          <p style={{ margin: "8px 0 0", fontSize: 12, color: "#8a2d2d" }}>
            {uploadError}
          </p>
        )}
      </div>

      {svg3dHtml ? (
        <FloorPlan3DViewer floors3d={{ "0": svg3dHtml }} floorCount={1} />
      ) : (
        <div style={{ padding: 16, fontSize: 12, color: C.inkLight }}>
          Upload an SVG exported by this app (or any compatible room-annotated SVG) to preview interactive 3D.
        </div>
      )}
    </div>
  );
}

function StatsBar({ floors, rooms, failed, warnCount, score }: {
  floors: number; rooms: number; failed: string[];
  warnCount: number; score?: FloorScore;
}) {
  const pills = [
    { label: "Floors",       value: floors, accent: C.accent },
    { label: "Rooms placed", value: rooms,  accent: C.accent },
    ...(score?.total ? [{
      label: `Grade ${score.grade}`,
      value: `${score.total}/100`,
      accent: score.total >= 80 ? "#4a8a4a" : score.total >= 60 ? "#8a7040" : "#b05a5a",
    }] : []),
    ...(failed.length > 0 ? [{ label: "Failed",   value: failed.length, accent: "#b05a5a" }] : []),
    ...(warnCount     > 0 ? [{ label: "Warnings", value: warnCount,     accent: "#b07a30" }] : []),
  ];
  return (
    <div style={styles.statsBar}>
      {pills.map(p => (
        <div key={p.label} style={{ ...styles.statPill, border: `1px solid ${p.accent}33` }}>
          <span style={{ ...styles.statValue, color: p.accent }}>{p.value}</span>
          <span style={styles.statLabel}>{p.label}</span>
        </div>
      ))}
    </div>
  );
}

function WarningsPanel({ warnings }: { warnings: string[] }) {
  const [open, setOpen] = useState(false);
  if (!warnings.length) return null;
  return (
    <div style={styles.warningsPanel}>
      <button style={styles.warningsToggle} onClick={() => setOpen(!open)}>
        <span style={{ color: "#8a7040", fontSize: 13 }}>⚠</span>
        <span style={{ fontSize: 12, fontWeight: 500, color: "#8a7040" }}>
          {warnings.length} warning{warnings.length > 1 ? "s" : ""}
        </span>
        <span style={{ marginLeft: "auto", fontSize: 11, color: "#8a7040" }}>{open ? "hide" : "show"}</span>
      </button>
      {open && (
        <ul style={styles.warningsList}>
          {warnings.map((w, i) => <li key={i} style={styles.warningItem}>{w}</li>)}
        </ul>
      )}
    </div>
  );
}

const MAKET_FIELD_LABELS: Record<string, string> = {
  prose_before_geometry: "Prose (before geometry)",
  design_moves: "Design moves (site-specific)",
  spatial_concept: "Spatial concept",
  zoning_diagram_words: "Zoning (N/E/S/W)",
  room_table_markdown: "Room table",
  wet_core_drainage: "Wet core & drainage",
  opening_schedule_markdown: "Opening schedule",
  door_discipline: "Door discipline",
  guest_walkthrough: "Guest walkthrough",
  family_walkthrough: "Family walkthrough",
  circulation_critique: "Circulation critique",
  risks_mitigations: "Risks & mitigations",
  anti_template_statement: "Anti-template (what we refused)",
};

function MaketDeliverablePanel({ data }: { data: Record<string, string> }) {
  const [open, setOpen] = useState(true);
  const entries = Object.entries(data).filter(
    ([, v]) => typeof v === "string" && v.trim().length > 0,
  );
  if (!entries.length) return null;
  return (
    <div style={{ ...styles.card, border: "1px solid #c8d4e8", background: "#f7f9fc" }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          ...styles.jsonToggle,
          background: "#eef2f8",
          width: "100%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontSize: 12, fontWeight: 600, color: "#3d4f6b", letterSpacing: "0.04em" }}>
          Maket-grade architect deliverable
        </span>
        <span style={{ fontSize: 11, color: C.inkLight }}>{open ? "hide" : "show"}</span>
      </button>
      {open && (
        <div style={{ padding: "12px 16px 16px", display: "flex", flexDirection: "column", gap: 16 }}>
          {entries.map(([key, val]) => (
            <div key={key}>
              <p style={{ ...styles.sectionLabel, marginBottom: 6, color: "#5a6b8a" }}>
                {MAKET_FIELD_LABELS[key] ?? key}
              </p>
              <div
                style={{
                  fontSize: 12,
                  color: C.inkMid,
                  lineHeight: 1.75,
                  whiteSpace: "pre-wrap",
                }}
              >
                {val}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReasoningPanel({ reasoning, validation }: { reasoning: string; validation: string }) {
  const [open, setOpen] = useState(false);
  if (!reasoning) return null;
  const severity = validation.includes("CRITICAL") ? "🔴" : validation.includes("WARNING") ? "🟡" : "🟢";
  return (
    <div style={styles.reasoningPanel}>
      <button style={styles.reasoningToggle} onClick={() => setOpen(!open)}>
        <span style={{ fontSize: 12, fontWeight: 600, color: C.accent }}>
          {severity} Architect&apos;s design reasoning
        </span>
        <span style={{ marginLeft: "auto", fontSize: 11, color: C.inkLight }}>{open ? "hide" : "show"}</span>
      </button>
      {open && (
        <div style={{ padding: "12px 16px" }}>
          <p style={{ ...styles.sectionLabel, marginBottom: 8 }}>Design Reasoning</p>
          <p style={{ fontSize: 12, color: C.inkMid, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>{reasoning}</p>
          {validation && (
            <>
              <p style={{ ...styles.sectionLabel, marginTop: 16, marginBottom: 8 }}>Validation Result</p>
              <pre style={styles.validationText}>{validation}</pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function SvgFloorCard({
  floorKey,
  svgStr,
  editorSlot,
}: {
  floorKey: string;
  svgStr: string;
  editorSlot?: ReactNode;
}) {
  const label = FLOOR_LABELS[floorKey] ?? `FLOOR ${floorKey}`;
  const slug  = floorSlug(floorKey);
  const trimmed = svgStr.trimStart();
  const scaledSvg = /^<svg\s/i.test(trimmed)
    ? trimmed.replace(/^<svg\s+/i, '<svg style="max-width:100%;height:auto;display:block" ')
    : trimmed;
  return (
    <div style={styles.floorCard}>
      <div style={styles.floorCardHeader}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={styles.floorBadge}>{label}</div>
          <span style={{ fontSize: 10, color: C.inkLight, letterSpacing: "0.06em",
                         textTransform: "uppercase" as const }}>
            2D · SVG · server-rendered
          </span>
        </div>
        <button style={styles.downloadBtn} onClick={() => downloadSvg(svgStr, `floor_plan_${slug}.svg`)}>
          ↓ SVG
        </button>
      </div>
      <p style={{ fontSize: 11, color: C.inkMid, lineHeight: 1.55, margin: "0 0 10px" }}>
        This drawing is produced by the layout engine and SVG renderer (walls, doors, windows, labels).
        {editorSlot ? (
          <>
            {" "}
            The <strong>wall-accurate editor</strong> below is the interactive plan—drag rooms and brown edge or
            corner handles there to stretch.
          </>
        ) : (
          <>
            {" "}
            Use the <strong>wall-accurate editor</strong> below to drag rooms and place doors/windows on walls (real openings in the SVG renderer), then re-run the same engine as the AI plan above.
            The separate <strong>Interactive 3D</strong> viewer still offers its own 2D tab for quick drags synced to Three.js.
          </>
        )}
      </p>
      {editorSlot ? (
        <p
          style={{
            margin: "0 0 12px",
            fontSize: 11,
            color: C.inkLight,
            lineHeight: 1.5,
            padding: "10px 14px",
            background: C.headerBg,
            borderRadius: 8,
            border: `1px dashed ${C.borderMid}`,
          }}
        >
          The live floor plan is only in the editor below—scroll to it to drag, stretch, and place openings.
        </p>
      ) : (
        <div style={{ ...styles.svgWrap, width: "100%" }}>
          <div style={{ width: "100%", maxWidth: "100%" }} dangerouslySetInnerHTML={{ __html: scaledSvg }} />
        </div>
      )}
      {editorSlot}
    </div>
  );
}

function DxfBar({ dxfPaths }: { dxfPaths: Record<string, string> }) {
  const entries = Object.entries(dxfPaths).filter(([, v]) => v);
  if (!entries.length) return null;
  return (
    <div style={styles.dxfBar}>
      <span style={styles.sectionLabel}>AutoCAD / DXF</span>
      {entries.map(([key]) => (
        <a key={key} href={`/download_dxf?floor=${key}`} download style={styles.downloadBtn}>
          ↓ {FLOOR_LABELS[key] ?? `Floor ${key}`} .dxf
        </a>
      ))}
    </div>
  );
}

function JsonPanel({ data }: { data: unknown }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={styles.jsonPanel}>
      <button style={styles.jsonToggle} onClick={() => setOpen(!open)}>
        <span style={styles.sectionLabel}>Parsed room program (JSON)</span>
        <span style={{ marginLeft: "auto", fontSize: 11, color: C.inkLight }}>
          {open ? "collapse" : "expand"}
        </span>
      </button>
      {open && (
        <pre style={styles.jsonPre}>
          <code>{JSON.stringify(data, null, 2)}</code>
        </pre>
      )}
    </div>
  );
}

// ── 3D Viewer ─────────────────────────────────────────────────────────────────
//
// WHY blob URL + <iframe src={blobUrl}>:
//   • dangerouslySetInnerHTML strips <script> tags — Three.js never loads
//   • srcdoc works but some browsers/CSPs block it for external scripts
//   • blob: URL gives the HTML its own browsing context, scripts execute normally
//   • sandbox="allow-scripts allow-same-origin allow-pointer-lock" for 3D iframe (pointer lock walk mode)
//     (same-origin because blob: URLs inherit the parent's origin)
//
// The renderer HTML detects _inIframe and does NOT subtract the side panel width
// from the canvas — the parent controls iframe sizing, so the canvas fills 100%.

function FloorPlan3DViewer({ floors3d, floorCount }: {
  floors3d:   Record<string, string>;
  floorCount: number;
}) {
  const [activeFloor, setActiveFloor]   = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [blobUrl, setBlobUrl]           = useState("");
  const iframeRef                       = useRef<HTMLIFrameElement>(null);

  const activeHtml = floors3d[String(activeFloor)] ?? "";

  // Convert HTML string → blob URL each time the active floor changes
  useEffect(() => {
    if (!activeHtml) { setBlobUrl(""); return; }
    const blob = new Blob([activeHtml], { type: "text/html" });
    const url  = URL.createObjectURL(blob);
    setBlobUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [activeHtml]);

  function downloadHtml() {
    if (!activeHtml) return;
    const blob = new Blob([activeHtml], { type: "text/html" });
    const url  = URL.createObjectURL(blob);
    Object.assign(document.createElement("a"), {
      href: url,
      download: `3d_floor_plan_${floorSlug(String(activeFloor))}.html`,
    }).click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const wrapStyle: React.CSSProperties = isFullscreen
    ? {
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        background: "#1a1714",
        width: "100%",
        height: "100dvh",
        maxHeight: "100dvh",
        minHeight: 0,
        boxSizing: "border-box",
        paddingTop: "env(safe-area-inset-top, 0px)",
        paddingBottom: "env(safe-area-inset-bottom, 0px)",
        paddingLeft: "env(safe-area-inset-left, 0px)",
        paddingRight: "env(safe-area-inset-right, 0px)",
      }
    : {
        display: "flex",
        flexDirection: "column",
        width: "100%",
        minHeight: 0,
        height: "clamp(480px, 76dvh, 900px)",
        borderRadius: 10,
        overflow: "hidden",
        boxSizing: "border-box",
        boxShadow: "inset 0 0 0 1px rgba(200,169,110,0.14)",
      };

  return (
    <div style={wrapStyle}>

      {/* Toolbar */}
      <div style={styles.threeDToolbar}>
        <div
          style={{
            display: "flex",
            gap: 4,
            flex: "1 1 0",
            minWidth: 0,
            overflowX: "auto",
            flexWrap: "nowrap" as const,
            WebkitOverflowScrolling: "touch",
          }}
        >
          {Array.from({ length: floorCount }, (_, i) => (
            <button
              key={i}
              onClick={() => setActiveFloor(i)}
              disabled={!floors3d[String(i)]}
              style={{
                ...styles.threeDTab,
                ...(activeFloor === i ? styles.threeDTabActive : {}),
                ...(!floors3d[String(i)] ? { opacity: 0.4, cursor: "not-allowed" } : {}),
              }}
            >
              {FLOOR_LABELS[String(i)] ?? `Floor ${i}`}
            </button>
          ))}
        </div>
        <div
          style={{
            display: "flex",
            gap: 6,
            flexShrink: 0,
            marginLeft: "auto",
            alignItems: "center",
          }}
        >
          <button style={styles.threeDIconBtn} onClick={downloadHtml} title="Download 3D HTML">
            Download
          </button>
          <button
            type="button"
            style={styles.threeDFullscreenBtn}
            onClick={() => setIsFullscreen((f) => !f)}
            title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? "Exit full screen" : "Full screen"}
          </button>
        </div>
      </div>

      {/* Hint bar */}
      <div style={styles.threeDHint}>
        Drag to orbit (or right-drag) · Arrows rotate view · Scroll zoom · Click room to focus · Front/Rear follow plan entrance
      </div>

      {/* iframe — key forces full remount on floor change so Three.js re-inits cleanly */}
      {blobUrl ? (
        <iframe
          key={blobUrl}
          ref={iframeRef}
          src={blobUrl}
          style={{ flex: 1, width: "100%", minHeight: 0, border: "none", display: "block" }}
          title={`3D Floor Plan — ${FLOOR_LABELS[String(activeFloor)] ?? `Floor ${activeFloor}`}`}
          sandbox="allow-scripts allow-same-origin allow-pointer-lock"
        />
      ) : (
        <div style={styles.threeDLoading}>
          <span style={styles.threeDSpinner} />
          Loading 3D model…
        </div>
      )}
    </div>
  );
}

function ThreeDCard({ floors3d, floorCount }: {
  floors3d:   Record<string, string>;
  floorCount: number;
}) {
  const [open, setOpen] = useState(true);

  const hasContent = Object.values(floors3d).some(
    v => typeof v === "string" && v.length > 100
  );
  if (!hasContent) return null;

  return (
    <div style={{ ...styles.floorCard, overflow: "visible" }}>
      <div style={styles.floorCardHeader}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ ...styles.floorBadge, background: "#1a1714",
                        color: "#c8a96e", border: "1px solid #3a3028" }}>
            3D VIEW
          </div>
          <span style={{ fontSize: 10, color: C.inkLight, letterSpacing: "0.06em",
                         textTransform: "uppercase" as const }}>
            Three.js · Orbit + Cutaway + Walkthrough
          </span>
        </div>
        <button style={styles.downloadBtn} onClick={() => setOpen(o => !o)}>
          {open ? "▲ Hide" : "▼ Show"}
        </button>
      </div>
      {open && (
        <div style={{ padding: "0 12px 14px", background: C.paper }}>
          <div
            style={{
              borderRadius: 12,
              overflow: "visible",
              boxShadow: "0 4px 28px rgba(44, 40, 32, 0.1), 0 0 0 1px rgba(62, 55, 45, 0.07)",
            }}
          >
            <FloorPlan3DViewer floors3d={floors3d} floorCount={floorCount} />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function ResultPanel({ result, isLoading = false, error = null, apiBase = "http://localhost:8000" }: ResultPanelProps) {
  const [floors3dPatch, setFloors3dPatch] = useState<Record<string, string>>({});

  useEffect(() => {
    setFloors3dPatch({});
  }, [result]);

  const floors3dMerged = useMemo(() => {
    if (!result) return {} as Record<string, string>;
    const base: Record<string, string> =
      result.floors_3d ??
      result.per_floor_3d ??
      (result.ground_floor_3d ? { "0": result.ground_floor_3d } : {});
    return { ...base, ...floors3dPatch };
  }, [result, floors3dPatch]);

  if (isLoading) return <LoadingState />;
  if (error)     return <ErrorState error={error} />;
  if (!result) {
    return (
      <div style={styles.root}>
        <EmptyState />
        <SvgUpload3DCard apiBase={apiBase} />
      </div>
    );
  }

  // SVG entries — supports new "floors" key and legacy "per_floor_svgs" / "ground_floor_svg"
  const svgSource = result.floors ?? result.per_floor_svgs;
  const svgEntries: Array<[string, string]> = svgSource
    ? Object.entries(svgSource)
        .filter(([, v]) => typeof v === "string" && v.trim().startsWith("<svg"))
        .sort(([a], [b]) => Number(a) - Number(b))
    : (result.ground_floor_svg?.trim().startsWith("<svg")
        ? [["0", result.ground_floor_svg]] : []);

  // 3D entries merged with layout-editor patches (see floors3dMerged above)
  const floors      = result.floors_generated ?? 1;
  const rooms       = result.rooms_placed     ?? 0;
  const failed      = result.rooms_failed     ?? [];
  const warnings    = result.warnings         ?? [];
  const groundScore = result.ground_score ?? result.scores?.["0"];

  const maketRaw =
    result.maket_deliverable ??
    (result.project_data?.maket_deliverable as Record<string, string> | undefined);
  const maketDeliverable: Record<string, string> =
    maketRaw && typeof maketRaw === "object"
      ? Object.fromEntries(
          Object.entries(maketRaw).filter(([, v]) => typeof v === "string") as [string, string][],
        )
      : {};

  return (
    <div style={styles.root}>
      <StatsBar floors={floors} rooms={rooms} failed={failed}
                warnCount={warnings.length} score={groundScore} />
      <WarningsPanel warnings={warnings} />
      <ReasoningPanel reasoning={result.design_reasoning ?? ""}
                      validation={result.validation ?? ""} />
      <MaketDeliverablePanel data={maketDeliverable} />

      {/* 2D SVG floor plans */}
      {svgEntries.length > 0
        ? svgEntries.map(([key, svg]) => {
            const rawLayout = result.layout_data?.[key];
            const layoutFloor =
              rawLayout && typeof rawLayout === "object" && !Array.isArray(rawLayout)
                ? (rawLayout as Record<string, unknown>)
                : {};
            const rooms = layoutFloor.rooms;
            const showEditor = Array.isArray(rooms) && rooms.length > 0;
            const fi = Number.parseInt(key, 10);
            const floorIx = Number.isFinite(fi) ? fi : 0;
            return (
              <SvgFloorCard
                key={key}
                floorKey={key}
                svgStr={svg}
                editorSlot={
                  showEditor ? (
                    <LayoutEditorPhaseA
                      floorKey={key}
                      floorIndex={floorIx}
                      layoutFloor={layoutFloor}
                      initialSvg={svg}
                      parsed={(result.project_data ?? {}) as Record<string, unknown>}
                      apiBase={apiBase}
                      onThreeDHtml={(fk, html) =>
                        setFloors3dPatch((prev) => ({ ...prev, [fk]: html }))
                      }
                    />
                  ) : null
                }
              />
            );
          })
        : (
          <div style={{ ...styles.card, border: "1px solid #DDD0A0", background: "#FDF8EC" }}>
            <p style={{ fontSize: 13, color: "#8a6030" }}>
              <strong>2D floor plan not available.</strong>{" "}
              Ensure <code style={{ fontFamily: "monospace" }}>svg_renderer.py</code> is in{" "}
              <code style={{ fontFamily: "monospace" }}>app/services/</code>.
            </p>
          </div>
        )
      }

      {/* 3D interactive viewer */}
      <ThreeDCard floors3d={floors3dMerged} floorCount={floors} />
      <SvgUpload3DCard apiBase={apiBase} />

      <DxfBar dxfPaths={result.dxf_paths ?? {}} />
      <JsonPanel data={result.project_data ?? result} />
    </div>
  );
}

// ── Design tokens ─────────────────────────────────────────────────────────────

const C = {
  paper:     "#FAF7F2",
  border:    "#DDD6CA",
  borderMid: "#C8BFB0",
  ink:       "#2C2820",
  inkMid:    "#6B6258",
  inkLight:  "#9A9080",
  accent:    "#5A6B4A",
  badgeBg:   "#EDE8DF",
  headerBg:  "#F2EDE4",
};

const styles: Record<string, React.CSSProperties> = {
  root:            { display: "flex", flexDirection: "column", gap: 16,
                     fontFamily: "'DM Sans', 'Helvetica Neue', sans-serif" },
  card:            { background: C.paper, border: `1px solid ${C.border}`,
                     borderRadius: 10, padding: 24 },
  loadingInner:    { display: "flex", alignItems: "center", gap: 16 },
  // animation name "spin" is defined by the @keyframes injected at module load
  spinner:         { width: 20, height: 20, flexShrink: 0, border: `2px solid ${C.border}`,
                     borderTopColor: C.accent, borderRadius: "50%",
                     animation: "spin 0.8s linear infinite" },
  loadingTitle:    { margin: 0, fontSize: 14, fontWeight: 500, color: C.ink, letterSpacing: "0.02em" },
  loadingSubtitle: { margin: "4px 0 0", fontSize: 12, color: C.inkLight, letterSpacing: "0.01em" },
  emptyText:       { margin: "6px 0 0", fontSize: 13, color: C.inkLight, lineHeight: 1.6 },
  statsBar:        { display: "flex", gap: 8, flexWrap: "wrap" as const },
  statPill:        { display: "flex", flexDirection: "column" as const, alignItems: "center",
                     background: C.paper, border: `1px solid ${C.border}`,
                     borderRadius: 8, padding: "8px 16px", minWidth: 72 },
  statValue:       { fontSize: 20, fontWeight: 600, lineHeight: 1, letterSpacing: "-0.02em" },
  statLabel:       { fontSize: 10, color: C.inkLight, marginTop: 3,
                     textTransform: "uppercase" as const, letterSpacing: "0.08em" },
  warningsPanel:   { background: "#FDF8EC", border: "1px solid #DDD0A0", borderRadius: 8, overflow: "hidden" },
  warningsToggle:  { display: "flex", alignItems: "center", gap: 8, width: "100%",
                     padding: "10px 16px", background: "none", border: "none",
                     cursor: "pointer", textAlign: "left" as const },
  warningsList:    { margin: 0, padding: "0 16px 12px 36px", listStyle: "disc" },
  warningItem:     { fontSize: 12, color: "#6a5520", lineHeight: 1.6, marginBottom: 4 },
  reasoningPanel:  { background: "#F2F7EE", border: "1px solid #C8D8B8", borderRadius: 8, overflow: "hidden" },
  reasoningToggle: { display: "flex", alignItems: "center", gap: 8, width: "100%",
                     padding: "10px 16px", background: "none", border: "none",
                     cursor: "pointer", textAlign: "left" as const },
  validationText:  { margin: 0, fontSize: 11, color: C.inkMid, lineHeight: 1.7,
                     whiteSpace: "pre-wrap" as const, fontFamily: "'DM Mono', monospace",
                     background: "#EEF4E8", padding: "8px 12px", borderRadius: 6 },
  floorCard:       { background: C.paper, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" },
  floorCardHeader: { display: "flex", alignItems: "center", justifyContent: "space-between",
                     padding: "12px 16px", background: C.headerBg,
                     borderBottom: `1px solid ${C.border}`, gap: 8 },
  floorBadge:      { fontSize: 11, fontWeight: 600, letterSpacing: "0.12em",
                     textTransform: "uppercase" as const, color: C.ink, background: C.badgeBg,
                     border: `1px solid ${C.borderMid}`, borderRadius: 4, padding: "3px 10px" },
  svgWrap:         { background: "#F5F0E8", padding: 16, lineHeight: 0,
                     overflowX: "auto", overflowY: "auto",
                     maxHeight: "min(92vh, 2000px)",
                     display: "flex", flexDirection: "column" as const, alignItems: "center" },
  dxfBar:          { display: "flex", flexWrap: "wrap" as const, alignItems: "center", gap: 8,
                     padding: "10px 16px", background: C.paper,
                     border: `1px solid ${C.border}`, borderRadius: 8 },
  downloadBtn:     { fontSize: 11, fontWeight: 500, color: C.accent, background: "none",
                     border: `1px solid ${C.accent}55`, borderRadius: 5,
                     padding: "4px 10px", cursor: "pointer",
                     letterSpacing: "0.04em", textDecoration: "none" },
  jsonPanel:       { background: C.paper, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" },
  jsonToggle:      { display: "flex", alignItems: "center", width: "100%",
                     padding: "12px 16px", background: C.headerBg, border: "none",
                     borderBottom: `1px solid ${C.border}`,
                     cursor: "pointer", textAlign: "left" as const },
  jsonPre:         { margin: 0, padding: 16, fontSize: 11, color: C.inkMid, lineHeight: 1.7,
                     overflowX: "auto" as const, fontFamily: "'DM Mono', 'Courier New', monospace",
                     background: "#FAF7F2", maxHeight: 500, overflowY: "auto" as const },
  sectionLabel:    { fontSize: 11, fontWeight: 600, textTransform: "uppercase" as const,
                     letterSpacing: "0.1em", color: C.inkMid, margin: 0 },
  threeDToolbar:   { display: "flex", alignItems: "center", justifyContent: "flex-start",
                     flexWrap: "wrap" as const, gap: 8,
                     padding: "8px 12px", background: "rgba(244,240,232,0.97)",
                     borderBottom: "1px solid #e5e1d8", flexShrink: 0 },
  threeDTab:       { padding: "5px 12px", borderRadius: 4, border: "1px solid #d8d0c0",
                     background: "transparent", fontSize: 11, fontFamily: "inherit",
                     color: "#5a5248", cursor: "pointer", letterSpacing: "0.04em",
                     transition: "all 0.12s" },
  threeDTabActive: { background: "#1a1714", color: "#c8a96e", border: "1px solid #1a1714" },
  threeDIconBtn:   { padding: "5px 10px", borderRadius: 4, border: "1px solid #d8d0c0",
                     background: "transparent", fontSize: 11, fontFamily: "inherit",
                     color: "#5a5248", cursor: "pointer", letterSpacing: "0.04em" },
  threeDFullscreenBtn: {
    padding: "6px 12px",
    borderRadius: 4,
    border: "1px solid #1a1714",
    background: "#1a1714",
    fontSize: 11,
    fontFamily: "inherit",
    fontWeight: 600,
    color: "#c8a96e",
    cursor: "pointer",
    letterSpacing: "0.03em",
    whiteSpace: "nowrap" as const,
  },
  threeDHint:      { fontSize: 10, color: "rgba(200,169,110,0.65)", padding: "4px 12px",
                     background: "rgba(26,23,20,0.97)", letterSpacing: "0.04em", flexShrink: 0 },
  threeDLoading:   { flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
                     gap: 10, color: "#c8a96e", fontSize: 13, background: "#1a1714",
                     fontFamily: "'DM Mono', monospace" },
  threeDSpinner:   { display: "inline-block", width: 16, height: 16,
                     border: "2px solid rgba(200,169,110,0.3)", borderTopColor: "#c8a96e",
                     borderRadius: "50%", animation: "spin 0.8s linear infinite" },
};