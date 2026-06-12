// ui.jsx — shared, theme-able primitives used by both directions.
// AdSlot: clearly-labelled ad inventory so the monetization map is legible.
// Ph: striped image placeholder with a monospace caption (what the photo is).

// ---- Image placeholder -------------------------------------------------
function Ph({ caption, h = 200, t, rounded = 0, style = {} }) {
  // t = theme: { stripeA, stripeB, ink }
  const stripeA = (t && t.stripeA) || "#e7e3dc";
  const stripeB = (t && t.stripeB) || "#ded9d0";
  const ink = (t && t.ink) || "rgba(40,34,28,0.55)";
  return (
    <div style={{
      height: h, width: "100%", borderRadius: rounded, overflow: "hidden",
      position: "relative",
      background: `repeating-linear-gradient(135deg, ${stripeA} 0 12px, ${stripeB} 12px 24px)`,
      display: "flex", alignItems: "flex-end", ...style,
    }}>
      <div style={{
        margin: 10, padding: "3px 7px", background: "rgba(255,255,255,0.82)",
        color: ink, font: "500 11px/1.2 'IBM Plex Mono', ui-monospace, monospace",
        letterSpacing: 0.2, borderRadius: 2, maxWidth: "85%",
      }}>▦ {caption}</div>
    </div>
  );
}

// ---- Ad slot -----------------------------------------------------------
// kind drives the caption; size is the px label. theme tokens keep it on-brand
// while still reading unmistakably as "this is an ad".
function AdSlot({ size = "970×250", kind = "Billboard", h = 250, t = {}, sticky = false, style = {} }) {
  const bg = t.bg || "#f4f1ea";
  const border = t.border || "#d8d1c4";
  const text = t.text || "rgba(40,34,28,0.5)";
  const accent = t.accent || "rgba(40,34,28,0.7)";
  return (
    <div style={{
      height: h, width: "100%", background: bg,
      border: `1px dashed ${border}`,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      gap: 6, position: "relative", borderRadius: t.radius || 0, ...style,
    }}>
      <span style={{
        position: "absolute", top: 7, left: 9,
        font: "600 9px/1 'IBM Plex Mono', ui-monospace, monospace",
        letterSpacing: 1.5, textTransform: "uppercase", color: text,
      }}>Advertisement</span>
      {sticky && <span style={{
        position: "absolute", top: 7, right: 9,
        font: "600 9px/1 'IBM Plex Mono', ui-monospace, monospace",
        letterSpacing: 1, textTransform: "uppercase", color: text, opacity: 0.8,
      }}>sticky</span>}
      <span style={{ font: "700 15px/1 'IBM Plex Mono', ui-monospace, monospace", color: accent, letterSpacing: 0.5 }}>{size}</span>
      <span style={{ font: "500 11px/1 'IBM Plex Mono', ui-monospace, monospace", color: text, letterSpacing: 1, textTransform: "uppercase" }}>{kind}</span>
    </div>
  );
}

Object.assign(window, { Ph, AdSlot });
