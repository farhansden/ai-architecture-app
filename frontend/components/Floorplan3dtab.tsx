// src/components/FloorPlan3DTab.jsx
// Drop this next to your existing floor plan SVG viewer.
// Reads `floors_3d` from the /generate API response.

import { useState, useRef, useEffect } from "react";

/**
 * FloorPlan3DTab
 *
 * Props:
 *   floors3d  : object  — { "0": "<html>...", "1": "<html>..." }
 *                         from API response key `floors_3d`
 *   floorCount: number  — total floors (default 1)
 */
export default function FloorPlan3DTab({ floors3d = {}, floorCount = 1 }) {
  const [activeFloor, setActiveFloor] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const iframeRef = useRef(null);

  const FLOOR_LABELS = { 0: "Ground Floor", 1: "First Floor", 2: "Second Floor", 3: "Third Floor" };

  // The HTML string for the currently selected floor
  const activeHtml = floors3d[String(activeFloor)] || "";

  // Convert HTML string → blob URL so the iframe can load it
  // (avoids CSP issues with srcdoc on some browsers)
  const [blobUrl, setBlobUrl] = useState("");
  useEffect(() => {
    if (!activeHtml) { setBlobUrl(""); return; }
    const blob = new Blob([activeHtml], { type: "text/html" });
    const url  = URL.createObjectURL(blob);
    setBlobUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [activeHtml]);

  // Nothing to render yet
  if (!floors3d || Object.keys(floors3d).length === 0) {
    return (
      <div style={styles.empty}>
        <div style={styles.emptyIcon}>⬡</div>
        <div style={styles.emptyTitle}>3D view not yet generated</div>
        <div style={styles.emptyHint}>
          Click <strong>Generate Design</strong> to build the 3D model
        </div>
      </div>
    );
  }

  // No HTML for this floor (placement failed, etc.)
  if (!activeHtml) {
    return (
      <div style={styles.empty}>
        <div style={styles.emptyIcon}>⚠</div>
        <div style={styles.emptyTitle}>3D not available for this floor</div>
        <div style={styles.emptyHint}>No rooms were placed on this floor</div>
      </div>
    );
  }

  return (
    <div style={{ ...styles.wrap, ...(isFullscreen ? styles.fullscreen : {}) }}>

      {/* ── Toolbar ── */}
      <div style={styles.toolbar}>

        {/* Floor tabs */}
        <div style={styles.tabs}>
          {Array.from({ length: floorCount }, (_, i) => (
            <button
              key={i}
              onClick={() => setActiveFloor(i)}
              style={{
                ...styles.tab,
                ...(activeFloor === i ? styles.tabActive : {}),
                ...(floors3d[String(i)] ? {} : styles.tabDisabled),
              }}
              disabled={!floors3d[String(i)]}
            >
              {FLOOR_LABELS[i] || `Floor ${i}`}
            </button>
          ))}
        </div>

        {/* Right controls */}
        <div style={styles.controls}>
          {/* Download button */}
          <button
            style={styles.iconBtn}
            title="Download 3D HTML"
            onClick={() => {
              const a = document.createElement("a");
              a.href = blobUrl;
              a.download = `3d_floor_plan_${FLOOR_LABELS[activeFloor]?.toLowerCase().replace(" ", "_")}.html`;
              a.click();
            }}
          >
            ↓ Download
          </button>

          {/* Fullscreen toggle */}
          <button
            style={styles.iconBtn}
            title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            onClick={() => setIsFullscreen(f => !f)}
          >
            {isFullscreen ? "⊠ Exit" : "⊞ Fullscreen"}
          </button>
        </div>
      </div>

      {/* ── Hint bar ── */}
      <div style={styles.hint}>
        Drag to orbit (or right-drag) · Arrow keys rotate · Scroll zoom · Click a room to focus · Panel: cutaway, lighting, walk
      </div>

      {/* ── iframe ── */}
      {blobUrl ? (
        <iframe
          ref={iframeRef}
          src={blobUrl}
          style={styles.iframe}
          title={`3D Floor Plan — ${FLOOR_LABELS[activeFloor]}`}
          sandbox="allow-scripts allow-same-origin allow-pointer-lock"
          loading="lazy"
        />
      ) : (
        <div style={styles.loading}>
          <span style={styles.spinner} />
          Generating 3D model…
        </div>
      )}
    </div>
  );
}


// ── Styles ────────────────────────────────────────────────────────────────────

const styles = {
  wrap: {
    display: "flex",
    flexDirection: "column",
    width: "100%",
    height: "600px",
    borderRadius: "8px",
    overflow: "hidden",
    border: "1px solid #e5e1d8",
    background: "#1a1714",
    fontFamily: "'DM Mono', 'Courier New', monospace",
  },
  fullscreen: {
    position: "fixed",
    inset: 0,
    zIndex: 9999,
    borderRadius: 0,
    height: "100vh",
    width: "100vw",
  },
  toolbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "8px 12px",
    background: "rgba(244,240,232,0.95)",
    borderBottom: "1px solid #e5e1d8",
    gap: "8px",
    flexShrink: 0,
  },
  tabs: {
    display: "flex",
    gap: "4px",
  },
  tab: {
    padding: "5px 12px",
    borderRadius: "4px",
    border: "1px solid #d8d0c0",
    background: "transparent",
    fontSize: "11px",
    fontFamily: "inherit",
    color: "#5a5248",
    cursor: "pointer",
    letterSpacing: "0.04em",
    transition: "all 0.12s",
  },
  tabActive: {
    background: "#1a1714",
    color: "#c8a96e",
    borderColor: "#1a1714",
  },
  tabDisabled: {
    opacity: 0.4,
    cursor: "not-allowed",
  },
  controls: {
    display: "flex",
    gap: "6px",
    alignItems: "center",
  },
  iconBtn: {
    padding: "5px 10px",
    borderRadius: "4px",
    border: "1px solid #d8d0c0",
    background: "transparent",
    fontSize: "11px",
    fontFamily: "inherit",
    color: "#5a5248",
    cursor: "pointer",
    letterSpacing: "0.04em",
    transition: "all 0.12s",
  },
  hint: {
    fontSize: "10px",
    color: "rgba(200,169,110,0.6)",
    padding: "4px 12px",
    background: "rgba(26,23,20,0.95)",
    letterSpacing: "0.04em",
    flexShrink: 0,
  },
  iframe: {
    flex: 1,
    width: "100%",
    border: "none",
    display: "block",
  },
  loading: {
    flex: 1,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "10px",
    color: "#c8a96e",
    fontSize: "13px",
    fontFamily: "inherit",
  },
  spinner: {
    display: "inline-block",
    width: "16px",
    height: "16px",
    border: "2px solid rgba(200,169,110,0.3)",
    borderTopColor: "#c8a96e",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  empty: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: "300px",
    gap: "8px",
    color: "#8a8070",
    fontFamily: "'DM Mono', monospace",
  },
  emptyIcon: {
    fontSize: "32px",
    color: "#c8a96e",
    opacity: 0.5,
  },
  emptyTitle: {
    fontSize: "14px",
    color: "#5a5248",
  },
  emptyHint: {
    fontSize: "12px",
    color: "#aaa098",
  },
};

// Inject keyframes once
if (typeof document !== "undefined") {
  const id = "__3d_spin_style";
  if (!document.getElementById(id)) {
    const s = document.createElement("style");
    s.id = id;
    s.textContent = "@keyframes spin { to { transform: rotate(360deg); } }";
    document.head.appendChild(s);
  }
}