# Handoff: Salacious News — Visual Refresh (Direction A · "PRESS" Tabloid)

## Overview
A full visual + UX refresh of **salacious.news**, a satirical/parody gossip news site. The
current site (Hugo) stacks every story in one flat, undifferentiated column with weak ad real
estate. This refresh introduces a real editorial hierarchy (lead hero → trending rail → latest
feed → category bands) and a **monetization-first ad layout** designed around **Google AdSense**.

The site's business goal is **ad revenue**, so ad placement is a first-class part of the design,
not an afterthought. The aesthetic is a **loud supermarket-tabloid** direction: newsprint, ink,
hot red, and highlighter yellow, with condensed "screamer" headlines.

Scope of this handoff: **Direction A**, across **three page types × two breakpoints**:
Homepage, Category (section) page, Article (single post) — each in **desktop (≥1024)** and
**mobile (<768)** layouts.

> A second, more premium "glossy gossip" direction (B) was also explored and rejected in favor of
> A. It is not included here; ask if you want it.

---

## About the Design Files
The files in this bundle are **design references created in HTML/React (JSX)** — prototypes that
communicate the intended look, layout, type, color, and ad placement. **They are not production
code to copy directly.**

The existing site is built with **Hugo (static site generator)**. The task is to **recreate these
designs as Hugo templates and partials**, using Hugo's templating, taxonomies, and page resources —
not to ship the React/JSX. Treat the JSX as an exact spec for markup structure, classes, and CSS
values. All styling is plain CSS (no framework); you can lift the CSS values directly into the
Hugo theme's stylesheet.

If you prefer, the CSS in `directionA.jsx` (the `TB_CSS` string) and `directionA-mobile.jsx`
(`TBM_CSS`) can be extracted almost verbatim into `.css` files — they are already plain, scoped CSS.

## Fidelity
**High-fidelity (hifi).** Final colors, typography, spacing, and interactions are specified. Recreate
the UI to match. Exact hex/oklch values, font families, sizes, weights, and line-heights are all
listed below and present in the source CSS.

One caveat: **images are placeholders.** Each placeholder contains a monospace caption describing
the photo that belongs there (e.g. "Taylor Swift wedding"). In production these are the per-article
images (AI-generated/original art, as the live site already uses).

---

## Design Tokens

### Color
Authoring used **oklch** as the source of truth; approximate hex is given for convenience.

| Token | oklch | ≈ hex | Use |
|---|---|---|---|
| `--paper` | — | `#f4efe4` | Page background (warm newsprint) |
| `--ink` | — | `#16120c` | Primary text, nav bar, masthead rules |
| `--red` | `oklch(0.55 0.21 26)` | `#d4241a` | Primary accent: kickers, links-hover, section bars, "NEWS" |
| `--red-d` | `oklch(0.46 0.20 28)` | `#b21a10` | Darker red (ad slot accents) |
| `--hi` | `oklch(0.88 0.17 96)` | `#f2ce00` | Highlighter yellow: ticker bg, "Most Read" header, accents |
| `--card` | — | `#fffdf8` | Card / panel surfaces |
| hairline | — | `#e3dccb` | Card dividers, list-row borders |
| body text | — | `#241f18` | Article body copy |
| dek / secondary | — | `#4a4337` | Story summaries |
| meta / muted | — | `#7a7160` · `#8a8170` | Bylines, dates, captions |
| anchor/footer bg | — | `#16120c` (`#211d17` ad inset) | Footer + sticky anchor |

### Typography
Three families + one mono. All from Google Fonts.

| Role | Family | Weights |
|---|---|---|
| Display "screamer" | **Anton** | 400 |
| Condensed headlines / labels / nav | **Oswald** | 500, 600, 700 |
| Body / UI / deks / meta | **Archivo** | 400, 500, 600, 700, 800, 900 (+ italic 400) |
| Ad labels / image captions | **IBM Plex Mono** | 500, 600, 700 |

Google Fonts URL (already used in the prototypes):
```
https://fonts.googleapis.com/css2?family=Anton&family=Oswald:wght@500;600;700&family=Archivo:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400&family=IBM+Plex+Mono:wght@500;600;700&display=swap
```

> **IMPORTANT — Anton metrics.** Anton has oversized vertical font metrics: its glyph ink box is
> ~1.5× the em. Use the **line-heights specified below** (they look tight but are tuned so the box
> contains the glyphs). If you tighten them further, following elements (deks) will visually
> collide with the last headline line. Do not set Anton headline `line-height` below the values given.

#### Desktop type scale
| Element | Family | Size / line-height | Tracking / transform |
|---|---|---|---|
| Masthead logo | Anton | 92px / 0.84 | uppercase; "Salacious" ink, "News" red |
| Lead hero `h1` | Anton | 44px / 1.16 | uppercase, `-0.005em` |
| Article `h1` | Anton | 46px / 1.18 | uppercase, `-0.005em` |
| Category `h1` | Anton | 58px / 1.34 | uppercase |
| "Most Read" rank numerals | Anton | 20px | red |
| Section header `h2` | Oswald 700 | 26px / 1 | uppercase |
| Card headline `h3` | Oswald 600 | 19px / 1.08 | uppercase |
| List-row headline | Oswald 600 | 18px / 1.1 | uppercase |
| Pull-quote | Oswald 600 | 24px / 1.3 | uppercase |
| Kicker chip | Oswald 700 | 11px / 1 | uppercase, `0.1em`, red bg / white text, padding `5px 10px 6px`, **white-space:nowrap** |
| Nav links | Oswald 600 | 14px / 1 | uppercase, `0.05em` |
| Body copy | Archivo 400 | 18px / 1.7 | — |
| Drop cap | Anton | 64px | red, `float:left` |
| Dek / summary | Archivo 500 | 13–19px / 1.45–1.5 | — |
| Meta (byline/date) | Archivo 600 | 11px / 1 | uppercase, `0.05em`; source in red |
| Ad label | IBM Plex Mono 600 | 9px / 1 | uppercase, `0.15em` |

#### Mobile type scale (<768)
| Element | Family | Size / line-height |
|---|---|---|
| Header wordmark | Anton | 23px / 1 |
| Hero `h1` | Anton | 27px / 1.2 |
| Article `h1` | Anton | 30px / 1.34 |
| Category `h1` | Anton | 40px / 1.42 |
| Card headline `h3` | Oswald 600 | 19px / 1.12 |
| List-row headline | Oswald 600 | 15px / 1.16 |
| Body copy | Archivo 400 | 16px / 1.7 |
| Drop cap | Anton | 50px |

### Spacing & layout
- **Desktop container:** `max-width: 1240px`, side padding `0 32px`, centered.
- **Main+rail grid:** `grid-template-columns: 1fr 300px; gap: 34px` (rail = right sidebar).
- **Card grid:** `repeat(3, 1fr); gap: 22px`.
- **List rows:** `grid-template-columns: 150px 1fr; gap: 16px` (thumbnail + text).
- **Hero:** `grid-template-columns: 1fr 360px; gap: 28px` (lead + trending rail).
- **Sticky offsets:** nav `top: 0`; sidebar ad group `top: 64px`.
- **Mobile:** fixed `390px` reference width; full-width single column, side padding `0 16px`.
- **Borders:** section header has a `14px` solid red bar filling remaining width; heavy section
  dividers are `2–3px solid var(--ink)`; hairlines `1px solid #e3dccb`.

### Misc
- Border radius: **0 everywhere** (sharp, tabloid). Ad slots use dashed 1px borders.
- Shadows: minimal; cards are flat. Only the canvas frame has shadow (presentation only — ignore).
- Image placeholders: 135° repeating-linear-gradient stripes + a monospace caption chip.

---

## Screens / Views

### 1. Homepage (`HomeA` / `MHomeA`)
**Purpose:** Front page; surface the lead story, trending, and the latest feed across categories;
maximize ad impressions without wrecking readability.

**Desktop layout (top → bottom):**
1. **Utility bar** (ink bg): left `★ Satire` red chip + date; right Newsletter / Instagram / Tip Line.
2. **Masthead** (centered): tiny flanking labels ("No. 1,492 / Daily Gossip", "No Fake News! / Guaranteed"),
   giant Anton wordmark **SALACIOUS** (ink) **NEWS** (red), tagline in tracked caps. 3px ink bottom rule.
3. **Nav** (ink bg, sticky): Home (red, active) + 7 categories + search; 1px separators between items;
   hover = red background.
4. **Breaking ticker** (highlighter-yellow bg, 2px ink borders): ink "⚡ Breaking" chip + 3 rotating headlines.
5. **Top ad — 970×250 billboard** (centered, max 970).
6. **Hero:** lead story (left, ~1fr) = full image with bottom gradient scrim + overlaid red kicker,
   Anton headline, dek, light meta. Right (360px) = **Trending Now** rail: ink header, ordered list of 5,
   big red Anton rank numerals.
7. **Body grid (1fr / 300px rail):**
   - Main: **"Latest News"** section header → 3-col card grid. The grid mixes story cards with **one
     native "Sponsored" card** (highlighter outline). Then an **in-feed 728×90** leaderboard. Then a
     **"World"** section as image-left list rows. Then a **"US"** section as small cards.
   - Rail (sticky): **300×250 MPU** → **Most Read** panel (yellow header, ranked list) → **300×600
     half-page** (sticky).
8. **"Around the Web"** advertorial: heavy ink top/bottom rules, 4-up native sponsored cards
   ("Sponsored Links · powered by ad network").
9. **Footer** (ink bg): big Anton "Salacious." wordmark, 3 link columns, legal/fair-use disclaimer,
   copyright.
10. **Sticky bottom anchor — 970×90** (dismissible ✕), pinned to viewport bottom.

**Mobile differences:**
- Compact **sticky header** (54px ink bar): ☰ menu, centered "Salacious News" wordmark, ⌕ search.
- **Horizontally-scrolling category strip** (sticky under header, 2px ink bottom border).
- Breaking ticker (single headline).
- **Top ad → 320×100** large mobile banner.
- Hero = full-bleed image + overlay.
- Trending rail moves **inline** (above the feed).
- Feed is single-column cards; **300×250 MPUs** are placed **in-content** between story clusters
  (the 300×600 has no mobile equivalent — its value moves to additional in-content 300×250s).
- Advertorial → 2-up grid.
- **Sticky anchor → 320×50** (AdSense anchor).

### 2. Category / Section page (`CatA` / `MCatA`)
**Purpose:** Section landing (e.g. Entertainment). Lead + paginated feed.

**Layout:** Same header/nav/footer/anchor as homepage. Then:
- **Top 970×250 billboard.**
- **Category masthead:** "Category" kicker → giant Anton category name → one-line description.
  3px ink bottom rule.
- Body grid (1fr / 300px rail):
  - Main: a **lead story** (dark hero card with "Top Story" badge) → 3-col cards → **728×90 in-list
    leaderboard** → image-left list rows, with a **970×90 native band** inserted after the 3rd row →
    pagination (numbered, active = ink fill).
  - Rail (sticky): **300×250 MPU** → **Trending Now** → **300×600 half-page**.
- **"Around the Web"** advertorial, footer, anchor.

**Mobile:** compact header + category strip; **320×100** top; category masthead (Anton 40px);
mobile hero "Top Story"; single-column cards; **300×250 in-feed MPU**; list rows; pagination;
advertorial 2-up; footer; **320×50 anchor**.

### 3. Article / Single post (`ArtA` / `MArtA`)
**Purpose:** Read one story; maximize in-content ad yield and "around the web" outbound clicks.

**Layout:** Header/nav, **top 970×250 billboard**, then body grid (1fr / 300px rail):
- Main (readable column, max ~720px): red kicker (`Category · Exclusive`) → Anton headline → large dek →
  byline/meta row with heavy ink bottom rule → hero image + caption → body paragraphs (first has red
  Anton **drop cap**) → **in-article 300×250 rectangle** (centered mid-content) → more paragraphs →
  red-rule **pull-quote** (Oswald caps) → final paragraphs → **"Around the Web"** advertorial →
  **"More in Entertainment"** related cards.
- Rail (sticky): **300×250 MPU** → **Trending Now** → **300×600 half-page**.
- Footer, **sticky 970×90 anchor**.

**Mobile:** compact header; **320×100** top; kicker/headline (Anton 30px)/dek/meta; hero image;
body with drop cap; **in-article 300×250**; pull-quote; advertorial 2-up; "More in" rows; footer;
**320×50 anchor**.

---

## Ad Inventory & AdSense Mapping
Every ad slot is rendered as a labelled placeholder in the mocks (dashed border, "ADVERTISEMENT"
eyebrow, size + role). Build each as an AdSense unit. **Reserve the slot's height** (CSS
`min-height`) to prevent layout shift (CLS), and keep the small "Advertisement" label above each.

| Placement | Desktop size | Mobile size | AdSense unit type | Notes |
|---|---|---|---|---|
| Top leaderboard | 970×250 (→728×90) | 320×100 | Responsive display | Below masthead; above the fold |
| In-feed leaderboard | 728×90 | — | Responsive display | Between feed clusters |
| In-feed / in-content MPU | 300×250 (rail) | 300×250 ×2 | Display | Mobile: in-content, lazy-load |
| Half-page (rail) | 300×600 | — | Display, **sticky** | Sticky `top:64px`; no mobile equiv |
| Native sponsored card | fluid (in grid) | fluid | **In-feed (fluid)** native | Styled to match story cards; label "Sponsored" |
| In-article rectangle | 300×250 | 300×250 | Display, **In-article** | Mid-content |
| "Around the Web" row | 4-up native | 2-up native | **Matched content / Multiplex** | High-RPM outbound |
| Bottom anchor | 970×90 | 320×50 | **Anchor / Auto ads** | Dismissible (✕) |

**AdSense implementation guidance**
- Prefer **responsive display units** (`data-ad-format="auto"`, `data-full-width-responsive="true"`)
  for the leaderboards so they adapt across breakpoints; the px sizes above are the design intent at
  each breakpoint.
- **Anchor** is easiest via **Auto ads** (anchor overlay) or a dedicated anchor unit. Keep the
  dismiss ✕ affordance shown in the mock.
- **Lazy-load** all below-the-fold slots.
- Respect policy: keep a healthy **content-to-ad ratio**, never push ads above the masthead, and
  ensure the sticky anchor + sticky half-page don't both crowd the first viewport on smaller laptops.
- Each `<ins class="adsbygoogle">` should sit inside a wrapper that renders the **"Advertisement"
  label** and reserves height.

---

## Interactions & Behavior
- **Sticky nav** (desktop) / **sticky compact header + category strip** (mobile) on scroll (`position: sticky; top: 0`).
- **Sticky rail ad group** (`position: sticky; top: 64px`) — MPU/half-page follow scroll within the body grid.
- **Sticky bottom anchor**, dismissible: clicking ✕ hides it (persist dismissal for the session via `sessionStorage`).
- **Card hover:** headline color → `--red` (transition ~0.12s). **Nav hover:** background → `--red`, text white.
- **Mobile category strip:** horizontal scroll (`overflow-x: auto`), active chip = red fill.
- **Breaking ticker:** the mock shows static headlines; in production animate as a horizontal marquee
  or rotate items (respect `prefers-reduced-motion` — pause/disable motion).
- **Search:** the ⌕ control opens search (existing site already supports search by category/title — wire to that).
- **Mobile menu (☰):** opens category/nav drawer.
- No client-side data fetching is required for layout — this is a static, content-driven Hugo site.
  The only JS state is: anchor dismissal, mobile menu open/close, ticker animation, and AdSense init.

## Responsive Behavior
The mocks are pinned at two widths (desktop **1440**, mobile **390**) but the implementation should be
fluid:
- **≥1024px:** full desktop layout (1fr/300px body grid, 3-col cards, hero 1fr/360px).
- **~768–1024px (tablet):** collapse the right rail beneath the main column (or 2-col cards); rail
  ads become in-content 300×250s. (Not separately mocked — follow desktop tokens, single-rail-below.)
- **<768px:** mobile layout (compact header, category strip, single column, mobile ad sizes).

---

## Hugo Implementation Notes
Suggested structure (adapt to the existing theme):

**Templates**
- `layouts/_default/baseof.html` — html shell, fonts, head, header/nav partials, footer, anchor.
- `layouts/index.html` — homepage (hero + trending + latest + category bands + advertorial).
- `layouts/_default/list.html` — category/section page.
- `layouts/_default/single.html` — article page.

**Partials**
- `header.html` (utility bar + masthead) and `nav.html` (sticky nav) — desktop; `header-mobile.html`
  + `category-strip.html` for mobile (or one responsive partial).
- `ticker.html` — breaking ticker.
- `ad-slot.html` — **parameterized**: takes `size`/`type`/`slot-id`; outputs the `<ins>` AdSense unit
  + "Advertisement" label + reserved height. Use this everywhere instead of repeating ad markup.
- `article-card.html` (image-top card), `article-row.html` (image-left row), `hero.html` (lead with scrim).
- `trending.html`, `most-read.html`, `advertorial.html`, `footer.html`, `anchor.html`.
- `native-card.html` — the in-feed "Sponsored" card.

**Content / front matter** (per post)
- `title`, `date`, `summary`/`dek`, `categories` (taxonomy: us, world, technology, entertainment,
  sports, politics, other), plus params: `source` (e.g. "TMZ", "Forbes"), `kicker` (optional),
  and the post image as a **page resource** (Hugo image render hooks / `.Resources`).
- "Trending" / "Most Read" can be driven by a manual front-matter flag, a weight, or a data file —
  pick what fits the existing content ops.

**CSS**
- Extract `TB_CSS` (from `src/directionA.jsx`) and `TBM_CSS` (from `src/directionA-mobile.jsx`) into
  the theme stylesheet. They are plain, already-scoped CSS (`.tb*` desktop, `.tbm*` mobile). Convert
  the breakpoint behavior from "two fixed widths" to media queries as described above.
- The mock scopes desktop under `.tb` and mobile under `.tbm`/`.tb`. In production you want **one
  responsive system** — merge them with media queries rather than shipping two parallel trees.

---

## State Management
Minimal (static content site):
- `anchorDismissed` (sessionStorage boolean) — bottom anchor.
- `mobileMenuOpen` (boolean) — ☰ drawer.
- Ticker rotation index (if animated).
- AdSense slots initialize on load / on lazy-load intersection.

No application data store, routing framework, or data fetching is required.

---

## Assets
- **No real images are shipped.** Placeholders carry a monospace caption naming the intended photo.
  In production these map to each article's image (the live site already uses per-article original/AI art).
- **Existing brand assets** on the live site: `img/banner.webp` (masthead) and
  `img/salacious-news-logo-alt.png` (footer). The refresh renders the wordmark as **live text** (Anton)
  rather than an image — you may keep the text wordmark (recommended, crisper + responsive) or swap in
  a refreshed banner image.
- **Fonts:** Anton, Oswald, Archivo, IBM Plex Mono (Google Fonts — URL above). Self-host for
  performance if the theme already self-hosts fonts.
- **Icons:** the few glyphs used (☰, ⌕, ✕, ★, ⚡, 🔥, ▸, ●) are Unicode in the mock. Replace with the
  theme's icon set if it has one; otherwise inline SVGs are fine.

---

## Files in this bundle
- `reference.html` — **open this in a browser** to see all 6 pages (3 desktop + 3 mobile) rendered
  and stacked. Self-contained (loads React/Babel from CDN + the `src/` files; needs internet for the CDN).
- `src/data.jsx` — sample content (real headlines/sources/dates from the live site) used by the mocks.
- `src/ui.jsx` — shared primitives: `AdSlot` (the labelled ad placeholder) and `Ph` (image placeholder).
- `src/directionA.jsx` — **desktop** Direction A: all CSS (`TB_CSS`) + components + `HomeA`/`CatA`/`ArtA`.
- `src/directionA-mobile.jsx` — **mobile** Direction A: all CSS (`TBM_CSS`) + components + `MHomeA`/`MCatA`/`MArtA`.

> The `src/*.jsx` files are React, but the styling is plain CSS and the markup is 1:1 with what the
> Hugo templates should output. Read them as the authoritative spec for structure, class names, and
> every color/size/spacing value.
