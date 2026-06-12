// directionA-mobile.jsx — DIRECTION A · mobile (390px) responsive layout.
// Reuses .tb design tokens (colors/fonts) + Ph/AdSlot. Layout is mobile-baked
// (single column, explicit widths) so it renders correctly at 390 regardless
// of viewport. AdSense-appropriate slots: 320×100 top, 300×250 in-feed/article,
// 320×50 sticky anchor, fluid native.

const TBM_CSS = `
.tbm{width:390px;background:var(--paper);}
.tbm *{box-sizing:border-box;}
.tbm a{color:inherit;text-decoration:none;}
.tbm-pad{padding:0 16px;}

/* sticky header */
.tbm-hd{position:sticky;top:0;z-index:30;background:#16120c;display:flex;align-items:center;
  height:54px;padding:0 14px;gap:12px;}
.tbm-hd .ic{color:#efe9da;font-size:20px;line-height:1;width:24px;}
.tbm-hd .lg{flex:1;text-align:center;font-family:'Anton';font-size:23px;line-height:1;text-transform:uppercase;color:#fff;letter-spacing:.01em;}
.tbm-hd .lg .r{color:var(--red);}
.tbm-hd .ic.s{text-align:right;}

/* category scroll strip */
.tbm-cats{background:var(--paper);border-bottom:2px solid var(--ink);display:flex;gap:0;overflow-x:auto;
  padding:0;position:sticky;top:54px;z-index:29;}
.tbm-cats a{flex:none;font:600 12px/1 'Oswald';text-transform:uppercase;letter-spacing:.04em;
  padding:11px 13px;color:var(--ink);border-right:1px solid #e3dccb;white-space:nowrap;}
.tbm-cats a.on{background:var(--red);color:#fff;}

/* ticker */
.tbm-tick{background:var(--hi);border-bottom:2px solid var(--ink);display:flex;align-items:center;gap:10px;
  height:34px;padding:0 12px;overflow:hidden;}
.tbm-tick .lab{background:var(--ink);color:var(--hi);font:700 10px/1 'Oswald';letter-spacing:.12em;
  text-transform:uppercase;padding:5px 7px;flex:none;white-space:nowrap;}
.tbm-tick .it{font:600 12px/1 'Archivo';white-space:nowrap;}

/* ad rail */
.tbm-ad{display:flex;justify-content:center;padding:16px;}

/* hero */
.tbm-hero{position:relative;}
.tbm-hero .scrim{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 36%,rgba(0,0,0,.82) 100%);}
.tbm-hero .ov{position:absolute;left:0;right:0;bottom:0;padding:16px;color:#fff;}
.tbm-hero h1{font-family:'Anton';font-weight:400;font-size:27px;line-height:1.2;text-transform:uppercase;
  margin:8px 0 9px;letter-spacing:-.005em;}
.tbm-hero .meta-l{color:#e9dfca;}
.tbm-hero .meta-l .src{color:var(--hi);}

/* section header */
.tbm-sec{display:flex;align-items:center;gap:10px;margin:0 0 14px;}
.tbm-sec h2{font:700 20px/1 'Oswald';text-transform:uppercase;margin:0;}
.tbm-sec .bar{height:11px;background:var(--red);flex:1;}
.tbm-sec .more{font:700 11px/1 'Oswald';text-transform:uppercase;letter-spacing:.06em;color:var(--red);}

/* feed card (single column, image left option) */
.tbm-card{display:block;padding:16px 0;border-bottom:1px solid #e3dccb;}
.tbm-card .img{margin-bottom:10px;}
.tbm-card h3{font:600 19px/1.12 'Oswald';text-transform:uppercase;margin:8px 0 7px;}
.tbm-card .dek{font:500 13px/1.45 'Archivo';color:#4a4337;margin:0 0 8px;}
.tbm-card:active h3{color:var(--red);}

/* split row (img left) */
.tbm-row{display:grid;grid-template-columns:108px 1fr;gap:13px;padding:14px 0;border-bottom:1px solid #e3dccb;align-items:start;}
.tbm-row h3{font:600 15px/1.16 'Oswald';text-transform:uppercase;margin:6px 0 6px;}

/* trending */
.tbm-trend{background:var(--card);border:2px solid var(--ink);margin:0 0 8px;}
.tbm-trend .hd{background:var(--ink);color:#fff;font:700 13px/1 'Oswald';letter-spacing:.08em;
  text-transform:uppercase;padding:10px 13px;}
.tbm-trend ol{margin:0;padding:0;list-style:none;}
.tbm-trend li{display:flex;gap:11px;padding:11px 13px;border-bottom:1px solid #e7e0d0;}
.tbm-trend li:last-child{border-bottom:0;}
.tbm-trend .n{font-family:'Anton';font-size:26px;line-height:.8;color:var(--red);flex:none;width:24px;}
.tbm-trend .tt{font:600 13px/1.2 'Archivo';}

/* advertorial 2-col */
.tbm-adv{border-top:3px solid var(--ink);border-bottom:3px solid var(--ink);padding:18px 0;}
.tbm-adv .hd{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:13px;}
.tbm-adv .hd h2{font:700 16px/1 'Oswald';text-transform:uppercase;margin:0;}
.tbm-adv .hd .by{font:600 8px/1 'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.08em;color:#8a8170;}
.tbm-adv-g{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.tbm-adv-c .sp{font:700 8px/1 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase;color:#a89e8a;}
.tbm-adv-c h4{font:600 13px/1.2 'Archivo';margin:6px 0 4px;}
.tbm-adv-c .br{font:600 10px/1 'Archivo';color:var(--red);}

/* footer */
.tbm-foot{background:var(--ink);color:#cfc7b6;padding:30px 16px 26px;}
.tbm-foot .fl{font:400 38px/.84 'Anton';text-transform:uppercase;color:#fff;}
.tbm-foot .fl .b{color:var(--red);}
.tbm-foot .nav{display:flex;flex-wrap:wrap;gap:9px 16px;margin:18px 0;font:600 12px/1 'Oswald';text-transform:uppercase;letter-spacing:.04em;}
.tbm-foot .disc{font:400 10.5px/1.6 'Archivo';color:#8c8474;border-top:1px solid #34302a;padding-top:16px;}
.tbm-foot .cr{font:600 10px/1 'Archivo';color:#8c8474;margin-top:14px;text-transform:uppercase;letter-spacing:.04em;}

/* sticky anchor */
.tbm-anchor{position:sticky;bottom:0;z-index:40;background:#16120cfa;border-top:2px solid var(--red);
  padding:6px 12px;display:flex;align-items:center;gap:10px;}
.tbm-anchor .cl{color:#9b937f;font:700 13px/1 'Archivo';flex:none;}
`;

function TbmStyle() { return <style dangerouslySetInnerHTML={{ __html: TBM_CSS }} />; }

const MBAR_AD = { bg: "#211d17", border: "#4a443a", text: "rgba(255,255,255,0.45)", accent: "var(--hi)" };

function MHeader({ active }) {
  return (
    <React.Fragment>
      <div className="tbm-hd">
        <span className="ic">☰</span>
        <span className="lg">Salacious<span className="r"> News</span></span>
        <span className="ic s">⌕</span>
      </div>
      <nav className="tbm-cats">
        {["US", "World", "Tech", "Entertainment", "Sports", "Politics", "Other"].map((c) => (
          <a key={c} className={c === active ? "on" : ""}>{c}</a>
        ))}
      </nav>
    </React.Fragment>
  );
}

function MTicker() {
  return (
    <div className="tbm-tick">
      <span className="lab">⚡ Breaking</span>
      <span className="it">{ARTICLES.trending[0].title}</span>
    </div>
  );
}

function MMeta({ a, light }) {
  return (
    <div className={"tb-meta" + (light ? " meta-l" : "")}>
      <span className="src">{a.source}</span><span className="dot">●</span><span>{a.date}</span>
    </div>
  );
}

function MAd({ size, kind, h, anchor }) {
  if (anchor) {
    return (
      <div className="tbm-anchor">
        <AdSlot size={size} kind={kind} h={h} t={MBAR_AD} style={{ flex: 1 }} />
        <span className="cl">✕</span>
      </div>
    );
  }
  return <div className="tbm-ad"><AdSlot size={size} kind={kind} h={h} t={TB_AD} style={{ maxWidth: size.split("×")[0] + "px" }} /></div>;
}

function MCard({ a }) {
  return (
    <a className="tbm-card">
      <div className="img"><Ph caption={a.img} h={196} t={TLIGHT} /></div>
      <span className="tb-kick ghost">{a.cat}</span>
      <h3>{a.title}</h3>
      {a.dek && <p className="dek">{a.dek}</p>}
      <MMeta a={a} />
    </a>
  );
}

function MNative() {
  return (
    <a className="tbm-card" style={{ background: "#fffdf8", outline: "2px solid var(--hi)", outlineOffset: -2, padding: 14, margin: "8px 0" }}>
      <div className="img"><Ph caption="Branded lifestyle shot" h={180} t={TLIGHT} /></div>
      <span className="tb-kick" style={{ background: "#8a8170" }}>Sponsored</span>
      <h3>This One Gut Trick Has Hollywood Publicists Furious</h3>
      <p className="dek">Promoted by GlowWell — the supplement everyone on set is whispering about.</p>
      <div className="tb-meta"><span style={{ color: "#8a8170" }}>Ad · GlowWell</span></div>
    </a>
  );
}

function MRow({ a }) {
  return (
    <a className="tbm-row">
      <Ph caption={a.img} h={78} t={TLIGHT} />
      <div><span className="tb-kick ghost">{a.cat}</span><h3>{a.title}</h3><MMeta a={a} /></div>
    </a>
  );
}

function MTrend() {
  return (
    <div className="tbm-trend">
      <div className="hd">🔥 Trending Now</div>
      <ol>
        {ARTICLES.trending.map((t, i) => (
          <li key={t.id}><span className="n">{i + 1}</span><span className="tt">{t.title}</span></li>
        ))}
      </ol>
    </div>
  );
}

function MSec({ title }) {
  return <div className="tbm-sec"><h2>{title}</h2><div className="bar" /><span className="more">More ▸</span></div>;
}

function MAdvertorial() {
  return (
    <div className="tbm-adv">
      <div className="hd"><h2>Around the Web</h2><span className="by">Sponsored · ad network</span></div>
      <div className="tbm-adv-g">
        {ARTICLES.advertorial.map((a) => (
          <a className="tbm-adv-c" key={a.id}>
            <div className="img" style={{ marginBottom: 8 }}><Ph caption={a.img} h={104} t={TLIGHT} /></div>
            <span className="sp">{a.label}</span>
            <h4>{a.title}</h4>
            <span className="br">{a.brand}</span>
          </a>
        ))}
      </div>
    </div>
  );
}

function MFooter() {
  return (
    <footer className="tbm-foot">
      <div className="fl">Salacious<span className="b">.</span></div>
      <div className="nav">{["US", "World", "Technology", "Entertainment", "Sports", "Politics", "Other", "Newsletter"].map((c) => <span key={c}>{c}</span>)}</div>
      <p className="disc">This website is a satirical news website. All articles are parodies of real news and are not intended to be taken seriously. Original articles are linked so readers can compare the two.</p>
      <div className="cr">© 2026 XYZ Consulting LLC · Privacy</div>
    </footer>
  );
}

// ---- PAGES -------------------------------------------------------------
function MHomeA() {
  const a = ARTICLES.lead;
  return (
    <div className="tb tbm">
      <TbStyle />
      <TbmStyle />
      <MHeader active="" />
      <MTicker />
      <MAd size="320×100" kind="AdSense — large mobile banner" h={100} />
      <a className="tbm-hero">
        <div className="img" style={{ position: "relative" }}><Ph caption={a.img} h={320} t={TDARK} /><div className="scrim" /></div>
        <div className="ov">
          <span className="tb-kick">Exclusive · {a.cat}</span>
          <h1>{a.title}</h1>
          <MMeta a={a} light />
        </div>
      </a>
      <div className="tbm-pad" style={{ paddingTop: 18 }}><MTrend /></div>
      <div className="tbm-pad" style={{ paddingTop: 14 }}>
        <MSec title="Latest News" />
        {ARTICLES.feed.slice(0, 2).map((x) => <MCard key={x.id} a={x} />)}
      </div>
      <MAd size="300×250" kind="AdSense — in-feed MPU" h={250} />
      <div className="tbm-pad">
        <MNative />
        {ARTICLES.feed.slice(2, 5).map((x) => <MCard key={x.id} a={x} />)}
      </div>
      <div className="tbm-pad" style={{ paddingTop: 18 }}>
        <MSec title="World" />
        {ARTICLES.byCat.World.map((x) => <MRow key={x.id} a={x} />)}
      </div>
      <MAd size="300×250" kind="AdSense — in-content MPU" h={250} />
      <div className="tbm-pad" style={{ paddingTop: 4 }}>
        <MSec title="US" />
        {ARTICLES.byCat.US.slice(0, 3).map((x) => <MRow key={x.id} a={x} />)}
      </div>
      <div className="tbm-pad" style={{ paddingTop: 18 }}><MAdvertorial /></div>
      <MFooter />
      <MAd size="320×50" kind="AdSense Anchor" h={50} anchor />
    </div>
  );
}

function MCatA() {
  const items = [...ARTICLES.feed, ...ARTICLES.byCat.World];
  return (
    <div className="tb tbm">
      <TbStyle />
      <TbmStyle />
      <MHeader active="Entertainment" />
      <MAd size="320×100" kind="AdSense — large mobile banner" h={100} />
      <div className="tbm-pad" style={{ borderBottom: "3px solid var(--ink)", paddingBottom: 12, marginBottom: 4 }}>
        <span className="tb-kick">Category</span>
        <h1 style={{ font: "400 40px/1.42 'Anton'", textTransform: "uppercase", margin: "0 0 6px" }}>Entertainment</h1>
        <p style={{ font: "500 13px/1.45 'Archivo'", color: "#4a4337", margin: 0 }}>Every breakup, blowup and box-office bloodbath — refreshed hourly.</p>
      </div>
      <a className="tbm-hero" style={{ display: "block" }}>
        <div className="img" style={{ position: "relative" }}><Ph caption={ARTICLES.lead.img} h={250} t={TDARK} /><div className="scrim" /></div>
        <div className="ov"><span className="tb-kick">Top Story</span><h1>{ARTICLES.lead.title}</h1><MMeta a={ARTICLES.lead} light /></div>
      </a>
      <div className="tbm-pad" style={{ paddingTop: 14 }}>
        {items.slice(0, 3).map((x) => <MCard key={x.id} a={x} />)}
      </div>
      <MAd size="300×250" kind="AdSense — in-feed MPU" h={250} />
      <div className="tbm-pad">
        {items.slice(3, 7).map((x) => <MRow key={x.id} a={x} />)}
        <div style={{ display: "flex", justifyContent: "center", gap: 6, margin: "20px 0 6px" }}>
          {["1", "2", "3", "▸"].map((p, i) => (
            <span key={i} style={{ font: "700 13px/1 'Oswald'", padding: "8px 13px", background: i === 0 ? "var(--ink)" : "var(--card)", color: i === 0 ? "#fff" : "var(--ink)", border: "1px solid var(--ink)" }}>{p}</span>
          ))}
        </div>
      </div>
      <div className="tbm-pad" style={{ paddingTop: 8 }}><MAdvertorial /></div>
      <MFooter />
      <MAd size="320×50" kind="AdSense Anchor" h={50} anchor />
    </div>
  );
}

function MArtA() {
  const a = ARTICLES.lead;
  const para = [
    "In a development nobody at the studio wanted to confirm on the record, the numbers came in over the weekend and they were, by every measure, a catastrophe. Insiders describe a war room of publicists refreshing the same spreadsheet, hoping the figure would change. It did not.",
    "\"We knew opening night was soft,\" said one executive who spoke on condition of anonymity. \"By Sunday we were drafting the streaming pivot. By Monday we were drafting our résumés.\"",
    "The pivot to paid streaming has only intensified the scrutiny. Analysts call it a face-saving maneuver; rivals call it a fire sale.",
    "What happens next is anyone's guess. But for the franchise's faithful, the message is clear: the universe may be vast, but the box office is unforgiving.",
  ];
  return (
    <div className="tb tbm">
      <TbStyle />
      <TbmStyle />
      <MHeader active="Entertainment" />
      <MAd size="320×100" kind="AdSense — large mobile banner" h={100} />
      <div className="tbm-pad" style={{ paddingTop: 6 }}>
        <span className="tb-kick" style={{ whiteSpace: "nowrap" }}>{a.cat} · Exclusive</span>
        <h1 style={{ font: "400 30px/1.34 'Anton'", textTransform: "uppercase", margin: "6px 0 14px", letterSpacing: "-.005em" }}>{a.title}</h1>
        <p style={{ font: "500 16px/1.5 'Archivo'", color: "#3c352b", margin: "0 0 14px" }}>{a.dek}</p>
        <div className="tb-meta" style={{ paddingBottom: 14, borderBottom: "2px solid var(--ink)", flexWrap: "wrap" }}>
          <span style={{ color: "#16120c" }}>By <b>The Salacious Desk</b></span><span className="dot">●</span><span className="src">{a.source}</span><span className="dot">●</span><span>{a.date}</span>
        </div>
      </div>
      <div style={{ margin: "16px 0" }}><Ph caption={a.img} h={240} t={TLIGHT} /></div>
      <div className="tbm-pad">
        <p style={{ font: "400 16px/1.7 'Archivo'", color: "#241f18", margin: "0 0 16px" }}><span style={{ font: "400 50px/.7 'Anton'", float: "left", color: "var(--red)", margin: "5px 10px 0 0" }}>I</span>{para[0]}</p>
        <p style={{ font: "400 16px/1.7 'Archivo'", color: "#241f18", margin: "0 0 16px" }}>{para[1]}</p>
      </div>
      <MAd size="300×250" kind="AdSense — in-article MPU" h={250} />
      <div className="tbm-pad">
        <p style={{ font: "400 16px/1.7 'Archivo'", color: "#241f18", margin: "0 0 16px" }}>{para[2]}</p>
        <blockquote style={{ borderLeft: "5px solid var(--red)", margin: "18px 0", padding: "2px 0 2px 16px", font: "600 20px/1.3 'Oswald'", textTransform: "uppercase" }}>"The universe may be vast, but the box office is unforgiving."</blockquote>
        <p style={{ font: "400 16px/1.7 'Archivo'", color: "#241f18", margin: "0 0 16px" }}>{para[3]}</p>
      </div>
      <div className="tbm-pad" style={{ paddingTop: 10 }}><MAdvertorial /></div>
      <div className="tbm-pad" style={{ paddingTop: 16 }}>
        <MSec title="More in Entertainment" />
        {ARTICLES.feed.slice(0, 3).map((x) => <MRow key={x.id} a={x} />)}
      </div>
      <MFooter />
      <MAd size="320×50" kind="AdSense Anchor" h={50} anchor />
    </div>
  );
}

Object.assign(window, { MHomeA, MCatA, MArtA });
