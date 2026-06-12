// directionA.jsx — DIRECTION A · "PRESS" loud supermarket tabloid.
// Newsprint + ink + hot red + highlighter yellow. Anton screamers, Oswald
// condensed decks. Scoped under .tb so it can't leak into Direction B.

const TB_CSS = `
.tb{--paper:#f4efe4;--ink:#16120c;--red:oklch(0.55 0.21 26);--red-d:oklch(0.46 0.20 28);
  --hi:oklch(0.88 0.17 96);--rule:#1612;--card:#fffdf8;
  background:var(--paper);color:var(--ink);font-family:'Archivo',system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;}
.tb *{box-sizing:border-box;}
.tb a{color:inherit;text-decoration:none;}
.tb-wrap{max-width:1240px;margin:0 auto;padding:0 32px;}

/* top utility bar */
.tb-util{background:#16120c;color:#cfc7b6;font:600 11px/1 'Archivo';letter-spacing:.06em;text-transform:uppercase;}
.tb-util .tb-wrap{display:flex;align-items:center;gap:18px;height:34px;}
.tb-util .tb-wrap>*{white-space:nowrap;}
.tb-util .sat{color:var(--paper);background:var(--red);padding:4px 8px;letter-spacing:.12em;}
.tb-util .sp{flex:1;}
.tb-util .lk{opacity:.8;}

/* masthead */
.tb-mast{text-align:center;padding:22px 0 14px;border-bottom:3px solid var(--ink);}
.tb-rule{height:0;border-top:1px solid var(--ink);max-width:1240px;margin:0 auto;}
.tb-logo{font-family:'Anton',sans-serif;font-weight:400;line-height:.84;letter-spacing:-.01em;
  text-transform:uppercase;margin:0;}
.tb-logo .a{font-size:92px;color:var(--ink);}
.tb-logo .b{font-size:92px;color:var(--red);-webkit-text-stroke:0;}
.tb-tag{font:600 12px/1 'Archivo';letter-spacing:.42em;text-transform:uppercase;color:var(--ink);
  margin-top:12px;opacity:.8;}
.tb-mast-side{position:absolute;top:0;font:600 11px/1.4 'Archivo';text-transform:uppercase;letter-spacing:.04em;color:#6b6253;}

/* nav */
.tb-nav{background:var(--ink);position:sticky;top:0;z-index:30;}
.tb-nav .tb-wrap{display:flex;align-items:stretch;gap:0;height:48px;}
.tb-nav a{color:#efe9da;font:600 14px/1 'Oswald';text-transform:uppercase;letter-spacing:.05em;
  display:flex;align-items:center;padding:0 16px;transition:.12s;}
.tb-nav a:hover{background:var(--red);color:#fff;}
.tb-nav a:not(.home){border-left:1px solid #2c2620;}
.tb-nav .home{background:var(--red);color:#fff;}
.tb-nav .spx{flex:1;}
.tb-nav .srch{display:flex;align-items:center;gap:8px;color:#a59c8b;padding-right:0;}

/* ticker */
.tb-tick{background:var(--hi);border-bottom:2px solid var(--ink);}
.tb-tick .tb-wrap{display:flex;align-items:center;gap:14px;height:36px;overflow:hidden;}
.tb-tick .lab{background:var(--ink);color:var(--hi);font:700 11px/1 'Oswald';letter-spacing:.14em;
  text-transform:uppercase;padding:6px 9px;flex:none;}
.tb-tick .it{font:600 13px/1 'Archivo';white-space:nowrap;color:#16120c;}
.tb-tick .dot{color:var(--red);font-weight:800;}

/* generic */
.tb-kick{display:inline-block;background:var(--red);color:#fff;font:700 11px/1 'Oswald';
  letter-spacing:.1em;text-transform:uppercase;padding:5px 10px 6px;margin-bottom:9px;white-space:nowrap;}
.tb-kick.ghost{background:none;color:var(--red);padding:0;border-bottom:2px solid var(--red);padding-bottom:3px;}
.tb-mark{background:var(--hi);padding:0 .12em;box-decoration-break:clone;-webkit-box-decoration-break:clone;}
.tb-meta{font:600 11px/1 'Archivo';text-transform:uppercase;letter-spacing:.05em;color:#7a7160;
  display:flex;gap:8px;align-items:center;}
.tb-meta .src{color:var(--red);}
.tb-meta .dot{opacity:.4;}

/* section header band */
.tb-sec{display:flex;align-items:center;gap:14px;margin:0 0 18px;}
.tb-sec h2{font:700 26px/1 'Oswald';text-transform:uppercase;letter-spacing:.01em;margin:0;color:var(--ink);}
.tb-sec .bar{height:14px;background:var(--red);flex:1;}
.tb-sec .more{font:700 12px/1 'Oswald';text-transform:uppercase;letter-spacing:.08em;color:var(--red);}

/* hero */
.tb-hero{display:grid;grid-template-columns:1fr 360px;gap:28px;padding:28px 0 6px;}
.tb-lead{position:relative;}
.tb-lead .img{position:relative;}
.tb-lead .scrim{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 38%,rgba(0,0,0,.78) 100%);}
.tb-lead .ov{position:absolute;left:0;right:0;bottom:0;padding:26px;color:#fff;}
.tb-lead h1{font-family:'Anton';font-weight:400;font-size:44px;line-height:1.16;text-transform:uppercase;
  margin:8px 0 14px;letter-spacing:-.005em;}
.tb-lead .dek{font:500 15px/1.45 'Archivo';color:#f2ece0;max-width:90%;margin-bottom:12px;}
.tb-lead .meta-l{color:#e9dfca;}
.tb-lead .meta-l .src{color:var(--hi);}

/* trending rail */
.tb-trend{background:var(--card);border:2px solid var(--ink);}
.tb-trend .hd{background:var(--ink);color:#fff;font:700 14px/1 'Oswald';letter-spacing:.1em;
  text-transform:uppercase;padding:11px 14px;display:flex;align-items:center;gap:8px;}
.tb-trend .hd .fire{color:var(--hi);}
.tb-trend ol{margin:0;padding:0;list-style:none;}
.tb-trend li{display:flex;gap:12px;padding:13px 14px;border-bottom:1px solid #e7e0d0;}
.tb-trend li:last-child{border-bottom:0;}
.tb-trend .n{font-family:'Anton';font-size:30px;line-height:.8;color:var(--red);flex:none;width:30px;}
.tb-trend .tt{font:600 14px/1.22 'Archivo';color:var(--ink);}
.tb-trend .tt .s{display:block;font:600 10px/1 'Archivo';text-transform:uppercase;letter-spacing:.05em;color:#a39a87;margin-top:5px;}

/* body grid */
.tb-body{display:grid;grid-template-columns:1fr 300px;gap:34px;padding:30px 0;}
.tb-aside{display:flex;flex-direction:column;gap:24px;}
.tb-stick{position:sticky;top:64px;display:flex;flex-direction:column;gap:24px;}

/* cards */
.tb-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;}
.tb-card .img{margin-bottom:11px;}
.tb-card h3{font:600 19px/1.08 'Oswald';text-transform:uppercase;margin:0 0 8px;color:var(--ink);}
.tb-card.sm h3{font-size:16px;}
.tb-card .dek{font:500 13px/1.45 'Archivo';color:#4a4337;margin:0 0 9px;}
.tb-card:hover h3{color:var(--red);}

/* list rows */
.tb-rows{display:flex;flex-direction:column;}
.tb-row{display:grid;grid-template-columns:150px 1fr;gap:16px;padding:16px 0;border-bottom:1px solid #e3dccb;}
.tb-row:first-child{padding-top:0;}
.tb-row h3{font:600 18px/1.1 'Oswald';text-transform:uppercase;margin:0 0 7px;}
.tb-row .dek{font:500 13px/1.4 'Archivo';color:#4a4337;margin:0 0 8px;}
.tb-row:hover h3{color:var(--red);}

/* most read */
.tb-mr{background:var(--card);border:2px solid var(--ink);}
.tb-mr .hd{background:var(--hi);color:var(--ink);font:700 13px/1 'Oswald';letter-spacing:.1em;
  text-transform:uppercase;padding:10px 13px;border-bottom:2px solid var(--ink);}
.tb-mr ol{margin:0;padding:6px 13px;list-style:none;counter-reset:m;}
.tb-mr li{counter-increment:m;display:flex;gap:11px;padding:11px 0;border-bottom:1px solid #ece5d5;}
.tb-mr li:last-child{border-bottom:0;}
.tb-mr li::before{content:counter(m);font-family:'Anton';font-size:20px;color:#c9bb9c;line-height:.9;}
.tb-mr .t{font:600 13px/1.25 'Archivo';}

/* advertorial */
.tb-adv{border-top:3px solid var(--ink);border-bottom:3px solid var(--ink);padding:22px 0;margin-top:8px;}
.tb-adv .hd{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:16px;}
.tb-adv .hd h2{font:700 18px/1 'Oswald';text-transform:uppercase;letter-spacing:.04em;margin:0;}
.tb-adv .hd .by{font:600 10px/1 'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.1em;color:#8a8170;}
.tb-adv-g{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;}
.tb-adv-c .img{margin-bottom:9px;}
.tb-adv-c .sp{font:700 9px/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#a89e8a;}
.tb-adv-c h4{font:600 14px/1.18 'Archivo';margin:5px 0 4px;}
.tb-adv-c .br{font:600 11px/1 'Archivo';color:var(--red);}

/* footer */
.tb-foot{background:var(--ink);color:#cfc7b6;padding:46px 0 30px;margin-top:10px;}
.tb-foot .top{display:flex;justify-content:space-between;gap:30px;border-bottom:1px solid #34302a;padding-bottom:24px;margin-bottom:22px;}
.tb-foot .fl{font:400 52px/.84 'Anton';text-transform:uppercase;}
.tb-foot .fl .b{color:var(--red);}
.tb-foot .cols{display:flex;gap:46px;}
.tb-foot h5{font:700 12px/1 'Oswald';letter-spacing:.1em;text-transform:uppercase;color:#fff;margin:0 0 12px;}
.tb-foot ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:8px;font:500 13px/1.3 'Archivo';}
.tb-foot .disc{font:400 11px/1.6 'Archivo';color:#8c8474;max-width:760px;margin-top:6px;}
.tb-foot .cr{font:600 11px/1 'Archivo';color:#8c8474;margin-top:20px;text-transform:uppercase;letter-spacing:.05em;}

/* sticky anchor */
.tb-anchor{position:sticky;bottom:0;z-index:40;background:#16120cfa;border-top:2px solid var(--red);}
.tb-anchor .tb-wrap{display:flex;justify-content:center;padding:9px 32px;position:relative;}
.tb-anchor .cl{position:absolute;right:32px;top:50%;transform:translateY(-50%);color:#9b937f;font:700 14px/1 'Archivo';}
`;

function TbStyle() { return <style dangerouslySetInnerHTML={{ __html: TB_CSS }} />; }

const TLIGHT = { stripeA: "#e7e1d2", stripeB: "#ddd6c4", ink: "rgba(40,34,24,0.6)" };
const TDARK = { stripeA: "#2a2520", stripeB: "#201c17", ink: "rgba(255,255,255,0.6)" };
const TB_AD = { bg: "#ece6d8", border: "#b9b0998c", text: "rgba(40,34,24,0.5)", accent: "var(--red-d)" };

function TbMeta({ a, light }) {
  return (
    <div className={"tb-meta" + (light ? " meta-l" : "")}>
      <span className="src">{a.source}</span><span className="dot">●</span><span>{a.date}</span>
    </div>
  );
}

function TbSec({ title }) {
  return (
    <div className="tb-sec">
      <h2>{title}</h2><div className="bar" /><span className="more">More ▸</span>
    </div>
  );
}

function TbCard({ a, sm }) {
  return (
    <a className={"tb-card" + (sm ? " sm" : "")}>
      <div className="img"><Ph caption={a.img} h={sm ? 130 : 168} t={TLIGHT} /></div>
      <span className="tb-kick ghost">{a.cat}</span>
      <h3 style={{ marginTop: 9 }}>{a.title}</h3>
      {a.dek && !sm && <p className="dek">{a.dek}</p>}
      <TbMeta a={a} />
    </a>
  );
}

function TbNav() {
  return (
    <nav className="tb-nav">
      <div className="tb-wrap">
        <a className="home">Home</a>
        {CATS.map((c) => <a key={c}>{c}</a>)}
        <span className="spx" />
        <a className="srch">⌕ Search</a>
      </div>
    </nav>
  );
}

function TbHeader() {
  return (
    <header>
      <div className="tb-util">
        <div className="tb-wrap">
          <span className="sat">★ Satire</span>
          <span className="lk">{ARTICLES.lead.date}</span>
          <span className="sp" />
          <span className="lk">Newsletter</span>
          <span className="lk">Instagram</span>
          <span className="lk">Tip Line</span>
        </div>
      </div>
      <div className="tb-mast">
        <div className="tb-wrap" style={{ position: "relative" }}>
          <span className="tb-mast-side" style={{ left: 32, textAlign: "left" }}>No. 1,492<br />Gossip Daily</span>
          <span className="tb-mast-side" style={{ right: 32, textAlign: "right" }}>Price<br />Your Soul</span>
          <h1 className="tb-logo"><span className="a">Salacious</span><span className="b"> News</span></h1>
          <div className="tb-tag">All the hot gossip from around the world</div>
        </div>
      </div>
      <TbNav />
    </header>
  );
}

function TbTicker() {
  return (
    <div className="tb-tick">
      <div className="tb-wrap">
        <span className="lab">⚡ Breaking</span>
        {ARTICLES.trending.slice(0, 3).map((t, i) => (
          <React.Fragment key={t.id}>
            {i > 0 && <span className="dot">●</span>}
            <span className="it">{t.title}</span>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function TbTrend() {
  return (
    <aside className="tb-trend">
      <div className="hd"><span className="fire">🔥</span> Trending Now</div>
      <ol>
        {ARTICLES.trending.map((t, i) => (
          <li key={t.id}>
            <span className="n">{i + 1}</span>
            <span className="tt">{t.title}<span className="s">{t.source}</span></span>
          </li>
        ))}
      </ol>
    </aside>
  );
}

function TbHero() {
  const a = ARTICLES.lead;
  return (
    <section className="tb-hero">
      <a className="tb-lead">
        <div className="img"><Ph caption={a.img} h={462} t={TDARK} /><div className="scrim" /></div>
        <div className="ov">
          <span className="tb-kick">Exclusive · {a.cat}</span>
          <h1>{a.title}</h1>
          <p className="dek">{a.dek}</p>
          <TbMeta a={a} light />
        </div>
      </a>
      <TbTrend />
    </section>
  );
}

function TbMostRead() {
  return (
    <div className="tb-mr">
      <div className="hd">Most Read</div>
      <ol>
        {ARTICLES.feed.slice(0, 5).map((a) => <li key={a.id}><span className="t">{a.title}</span></li>)}
      </ol>
    </div>
  );
}

function TbNative() {
  return (
    <a className="tb-card" style={{ outline: "2px solid var(--hi)", outlineOffset: 6 }}>
      <div className="img" style={{ position: "relative" }}>
        <Ph caption="Branded lifestyle shot" h={168} t={TLIGHT} />
      </div>
      <span className="tb-kick" style={{ background: "#8a8170" }}>Sponsored</span>
      <h3 style={{ marginTop: 9 }}>This One Gut Trick Has Hollywood Publicists Furious</h3>
      <p className="dek">Promoted by GlowWell — the supplement everyone on set is whispering about.</p>
      <div className="tb-meta"><span style={{ color: "#8a8170" }}>Ad · GlowWell</span></div>
    </a>
  );
}

function TbAdvertorial() {
  return (
    <section className="tb-adv">
      <div className="tb-wrap" style={{ padding: 0 }}>
        <div className="hd"><h2>Around the Web</h2><span className="by">Sponsored Links · powered by ad network</span></div>
        <div className="tb-adv-g">
          {ARTICLES.advertorial.map((a) => (
            <a className="tb-adv-c" key={a.id}>
              <div className="img"><Ph caption={a.img} h={132} t={TLIGHT} /></div>
              <span className="sp">{a.label}</span>
              <h4>{a.title}</h4>
              <span className="br">{a.brand}</span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

function TbFooter() {
  return (
    <footer className="tb-foot">
      <div className="tb-wrap">
        <div className="top">
          <div className="fl">Salacious<span className="b">.</span></div>
          <div className="cols">
            <div><h5>Sections</h5><ul>{CATS.slice(0, 4).map((c) => <li key={c}>{c}</li>)}</ul></div>
            <div><h5>More</h5><ul>{CATS.slice(4).map((c) => <li key={c}>{c}</li>)}<li>Newsletter</li></ul></div>
            <div><h5>Follow</h5><ul><li>Instagram</li><li>Tip Line</li><li>info@salacious.news</li></ul></div>
          </div>
        </div>
        <h5 style={{ color: "#fff" }}>Legal Disclaimer</h5>
        <p className="disc">This website is a satirical news website. All articles are parodies of real news and are not intended to be taken seriously. Original articles that have been parodied are linked so readers can compare the two. Use of copyrighted material falls under fair use for the purpose of parody and criticism.</p>
        <div className="cr">© 2026 XYZ Consulting LLC · Privacy Policy</div>
      </div>
    </footer>
  );
}

function TbAnchor() {
  return (
    <div className="tb-anchor">
      <div className="tb-wrap">
        <AdSlot size="970×90" kind="Sticky Anchor" h={66} t={{ bg: "#211d17", border: "#4a443a", text: "rgba(255,255,255,0.45)", accent: "var(--hi)" }} style={{ maxWidth: 970 }} />
        <span className="cl">✕</span>
      </div>
    </div>
  );
}

// ---- PAGES -------------------------------------------------------------
function HomeA() {
  return (
    <div className="tb">
      <TbStyle />
      <TbHeader />
      <TbTicker />
      <div className="tb-wrap" style={{ paddingTop: 22 }}>
        <AdSlot size="970×250" kind="Billboard — top leaderboard" h={244} t={TB_AD} style={{ maxWidth: 970, margin: "0 auto" }} />
      </div>
      <div className="tb-wrap"><TbHero /></div>
      <div className="tb-wrap">
        <div className="tb-body">
          <main>
            <TbSec title="Latest News" />
            <div className="tb-cards">
              {ARTICLES.feed.slice(0, 2).map((a) => <TbCard key={a.id} a={a} />)}
              <TbNative />
              {ARTICLES.feed.slice(2, 6).map((a) => <TbCard key={a.id} a={a} />)}
            </div>

            <div style={{ height: 30 }} />
            <AdSlot size="728×90" kind="In-feed leaderboard" h={96} t={TB_AD} style={{ maxWidth: 728, margin: "0 auto" }} />
            <div style={{ height: 30 }} />

            <TbSec title="World" />
            <div className="tb-rows">
              {ARTICLES.byCat.World.map((a) => (
                <a className="tb-row" key={a.id}>
                  <Ph caption={a.img} h={96} t={TLIGHT} />
                  <div><span className="tb-kick ghost">{a.cat}</span><h3 style={{ marginTop: 8 }}>{a.title}</h3>{a.dek && <p className="dek">{a.dek}</p>}<TbMeta a={a} /></div>
                </a>
              ))}
            </div>

            <div style={{ height: 30 }} />
            <TbSec title="US" />
            <div className="tb-cards">{ARTICLES.byCat.US.map((a) => <TbCard key={a.id} a={a} sm />)}</div>
          </main>

          <aside className="tb-aside">
            <div className="tb-stick">
              <AdSlot size="300×250" kind="MPU" h={250} t={TB_AD} />
              <TbMostRead />
              <AdSlot size="300×600" kind="Half-page · sticky" h={600} t={TB_AD} sticky />
            </div>
          </aside>
        </div>
      </div>
      <div className="tb-wrap"><TbAdvertorial /></div>
      <TbFooter />
      <TbAnchor />
    </div>
  );
}

function CatA() {
  const items = [...ARTICLES.feed, ...ARTICLES.byCat.World, ...ARTICLES.byCat.US];
  return (
    <div className="tb">
      <TbStyle />
      <TbHeader />
      <div className="tb-wrap" style={{ paddingTop: 22 }}>
        <AdSlot size="970×250" kind="Billboard — top leaderboard" h={244} t={TB_AD} style={{ maxWidth: 970, margin: "0 auto" }} />
      </div>
      <div className="tb-wrap" style={{ paddingTop: 26 }}>
        <div style={{ borderBottom: "3px solid var(--ink)", paddingBottom: 14, marginBottom: 6 }}>
          <span className="tb-kick">Category</span>
          <h1 style={{ font: "400 58px/1.34 'Anton'", textTransform: "uppercase", margin: "2px 0 8px" }}>Entertainment</h1>
          <p style={{ font: "500 15px/1.4 'Archivo'", color: "#4a4337", maxWidth: 620 }}>Every breakup, blowup and box-office bloodbath — refreshed hourly.</p>
        </div>
      </div>
      <div className="tb-wrap">
        <div className="tb-body">
          <main>
            <a className="tb-lead" style={{ display: "block", marginBottom: 26 }}>
              <div className="img" style={{ position: "relative" }}><Ph caption={ARTICLES.lead.img} h={360} t={TDARK} /><div className="scrim" /></div>
              <div className="ov"><span className="tb-kick">Top Story</span><h1>{ARTICLES.lead.title}</h1><TbMeta a={ARTICLES.lead} light /></div>
            </a>
            <div className="tb-cards">{ARTICLES.feed.slice(0, 3).map((a) => <TbCard key={a.id} a={a} />)}</div>
            <div style={{ height: 28 }} />
            <AdSlot size="728×90" kind="In-list leaderboard" h={96} t={TB_AD} style={{ maxWidth: 728, margin: "0 auto" }} />
            <div style={{ height: 28 }} />
            <div className="tb-rows">
              {items.slice(0, 6).map((a, i) => (
                <React.Fragment key={a.id + i}>
                  <a className="tb-row">
                    <Ph caption={a.img} h={96} t={TLIGHT} />
                    <div><span className="tb-kick ghost">{a.cat}</span><h3 style={{ marginTop: 8 }}>{a.title}</h3>{a.dek && <p className="dek">{a.dek}</p>}<TbMeta a={a} /></div>
                  </a>
                  {i === 2 && <div style={{ padding: "8px 0" }}><AdSlot size="970×90" kind="In-feed native band" h={84} t={TB_AD} /></div>}
                </React.Fragment>
              ))}
            </div>
            <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 26 }}>
              {["1", "2", "3", "4", "▸"].map((p, i) => (
                <span key={i} style={{ font: "700 14px/1 'Oswald'", padding: "9px 14px", background: i === 0 ? "var(--ink)" : "var(--card)", color: i === 0 ? "#fff" : "var(--ink)", border: "1px solid var(--ink)" }}>{p}</span>
              ))}
            </div>
          </main>
          <aside className="tb-aside">
            <div className="tb-stick">
              <AdSlot size="300×250" kind="MPU" h={250} t={TB_AD} />
              <TbTrend />
              <AdSlot size="300×600" kind="Half-page · sticky" h={600} t={TB_AD} sticky />
            </div>
          </aside>
        </div>
      </div>
      <div className="tb-wrap"><TbAdvertorial /></div>
      <TbFooter />
      <TbAnchor />
    </div>
  );
}

function ArtA() {
  const a = ARTICLES.lead;
  const para = [
    "In a development nobody at the studio wanted to confirm on the record, the numbers came in over the weekend and they were, by every measure, a catastrophe. Insiders describe a war room of publicists refreshing the same spreadsheet, hoping the figure would change. It did not.",
    "\"We knew opening night was soft,\" said one executive who spoke on condition of anonymity because they were not authorized to speak — or, frankly, to still have a job. \"By Sunday we were drafting the streaming pivot. By Monday we were drafting our résumés.\"",
    "The pivot to paid streaming, announced in a hastily-worded press release, has only intensified the scrutiny. Analysts call it a face-saving maneuver; rivals call it a fire sale; and at least one rival studio chief reportedly called it \"the funniest thing to happen all quarter.\"",
    "What happens next is anyone's guess. But for the franchise's faithful, the message is clear: the universe may be vast, but the box office is unforgiving.",
  ];
  return (
    <div className="tb">
      <TbStyle />
      <TbHeader />
      <div className="tb-wrap" style={{ paddingTop: 22 }}>
        <AdSlot size="970×250" kind="Billboard — top leaderboard" h={244} t={TB_AD} style={{ maxWidth: 970, margin: "0 auto" }} />
      </div>
      <div className="tb-wrap">
        <div className="tb-body" style={{ gridTemplateColumns: "1fr 300px", paddingTop: 30 }}>
          <main>
            <div style={{ maxWidth: 720 }}>
              <span className="tb-kick" style={{ marginBottom: 16, whiteSpace: "nowrap" }}>{a.cat} · Exclusive</span>
              <h1 style={{ font: "400 46px/1.18 'Anton'", textTransform: "uppercase", margin: "0 0 20px", letterSpacing: "-.005em" }}>{a.title}</h1>
              <p style={{ font: "500 19px/1.5 'Archivo'", color: "#3c352b", margin: "0 0 16px" }}>{a.dek}</p>
              <div className="tb-meta" style={{ paddingBottom: 16, borderBottom: "2px solid var(--ink)", marginBottom: 0 }}>
                <span style={{ color: "#16120c" }}>By <b>The Salacious Desk</b></span><span className="dot">●</span><span className="src">{a.source}</span><span className="dot">●</span><span>{a.date}</span>
                <span style={{ flex: 1 }} /><span>Share ▸</span>
              </div>
            </div>
            <div style={{ margin: "20px 0" }}><Ph caption={a.img} h={420} t={TLIGHT} /><div style={{ font: "500 11px/1.4 'Archivo'", color: "#8a8170", marginTop: 7 }}>Photo illustration · Salacious News</div></div>
            <div style={{ maxWidth: 720 }}>
              <p style={{ font: "400 18px/1.7 'Archivo'", color: "#241f18", margin: "0 0 18px" }}><span style={{ font: "400 64px/.7 'Anton'", float: "left", color: "var(--red)", margin: "6px 12px 0 0" }}>I</span>{para[0]}</p>
              <p style={{ font: "400 18px/1.7 'Archivo'", color: "#241f18", margin: "0 0 18px" }}>{para[1]}</p>
              <div style={{ margin: "26px 0" }}><AdSlot size="300×250" kind="In-article rectangle" h={250} t={TB_AD} style={{ maxWidth: 336, margin: "0 auto" }} /></div>
              <p style={{ font: "400 18px/1.7 'Archivo'", color: "#241f18", margin: "0 0 18px" }}>{para[2]}</p>
              <blockquote style={{ borderLeft: "5px solid var(--red)", margin: "22px 0", padding: "4px 0 4px 20px", font: "600 24px/1.3 'Oswald'", textTransform: "uppercase", color: "var(--ink)" }}>"The universe may be vast, but the box office is unforgiving."</blockquote>
              <p style={{ font: "400 18px/1.7 'Archivo'", color: "#241f18", margin: "0 0 18px" }}>{para[3]}</p>
            </div>
            <div style={{ marginTop: 30 }}><TbAdvertorial /></div>
            <div style={{ marginTop: 30 }}>
              <TbSec title="More in Entertainment" />
              <div className="tb-cards">{ARTICLES.feed.slice(0, 3).map((x) => <TbCard key={x.id} a={x} sm />)}</div>
            </div>
          </main>
          <aside className="tb-aside">
            <div className="tb-stick">
              <AdSlot size="300×250" kind="MPU" h={250} t={TB_AD} />
              <TbTrend />
              <AdSlot size="300×600" kind="Half-page · sticky" h={600} t={TB_AD} sticky />
            </div>
          </aside>
        </div>
      </div>
      <TbFooter />
      <TbAnchor />
    </div>
  );
}

Object.assign(window, { HomeA, CatA, ArtA });
