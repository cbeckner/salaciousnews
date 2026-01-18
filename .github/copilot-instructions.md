# Salacious News - Hugo Static Site

## Architecture Overview

This is a **Hugo-based static news site** with category-based content organization. The site uses the custom `news` theme (not `mainroad`) located in `themes/news/`. Content is organized by 7 main categories: Business, Entertainment, Other, Politics, Sports, Technology, US, and World.

## Key Components

### Content Structure
- **Content files**: All articles live in `content/<Category>/<slug>.md`
- **Required frontmatter fields**:
  - `Title`: Article headline (often clickbait-style)
  - `Description`: Meta description
  - `Date`: Publication date (format: `2023-08-14T08:19:40.0000000Z`)
  - `Categories`: Array with single category (e.g., `[Entertainment]`)
  - `Tags`: Relevant tags for the article
  - `Featured`: Boolean for featured articles
  - `Thumbnail.Src`: Relative path to image (e.g., `./img/posts/<uuid>.webp`)
  - `Source`: Original source (e.g., "CNN")
  - `OriginalUrl`: Link to original article
  - `ImagePrompt`: Description of the article image
- **Shortcodes**: Articles use `{{< articlead >}}` shortcode to inject Google AdSense ads mid-article

### Theme Architecture (`themes/news/`)
- **Layout files**: 
  - `layouts/index.html`: Homepage composition using partials
  - `layouts/_default/single.html`: Individual article template
  - `layouts/_default/list.html`: Category listing pages
- **Partials**: Modular components in `layouts/partials/`
  - `articlelist-type1.html`, `articlelist-type2.html`: Different article list styles
  - `articlelist-grouped.html`: Multi-category grouping
  - `trends.html`, `latestnews.html`: Homepage sections
  - `ad-banner1.html`, `ad-banner2.html`: Ad placements
- **Shortcodes**: `layouts/shortcodes/articlead.html` renders inline Google AdSense ads

### Hugo Configuration (`hugo.toml`)
- **Base URL**: `https://salacious.news/`
- **Active theme**: `news` (not mainroad)
- **Main sections**: 7 categories defined in `mainSections` and `subSections`
- **Google Analytics**: ID `G-MRRZYLYQC7`
- **Key params**:
  - Paginate: 10 posts per page
  - Highlight color: `#3ba5a9` (teal)
  - Sidebar widgets: search, recent, categories, social
  - Social: Instagram (`salacious_news`), email (`info@salacious.news`)

### Build System
- **PostCSS**: Uses PurgeCSS to remove unused CSS in production
- **CSS optimization**: `postcss.config.js` reads `hugo_stats.json` for used classes/tags
- **Production trigger**: Set `HUGO_ENVIRONMENT=production` for CSS purging
- **Dependencies**: Minimal - only PostCSS and PurgeCSS tools

## Development Workflows

### Running the site locally
```bash
hugo server -D    # Serves with drafts
hugo server       # Production-like preview
```

### Building for production
```bash
HUGO_ENVIRONMENT=production hugo --minify
```

### Deployment
- **Automated via GitHub Actions** → deploys to AWS S3
- Site builds on push to main branch
- Production environment variable triggers CSS optimization

### Creating new content (currently manual, automation in progress)
```bash
hugo new content/<Category>/<slug>.md
```
Then edit to match the required frontmatter structure (see Content Structure above).

**Automation goals** (agent development in `agent/` folder):
- Automated article generation from news sources
- AI image generation from `ImagePrompt` field
- End-to-end content pipeline from source → article → image → publish

### CSS changes
- Modify theme CSS in `themes/news/assets/` or `assets/`
- Hugo automatically processes PostCSS
- In production, PurgeCSS strips unused styles based on `hugo_stats.json`

## Project Conventions

### Article Filename Pattern
Format: `<descriptive-slug>-<5-char-hex>.md` (e.g., `barbie-box-office-3b9e9.md`)

### Image Handling
- Article images stored in `static/img/posts/` and `content/<Category>/img/posts/`
- Images referenced relative to content file: `./img/posts/<uuid>.webp`
- Thumbnails displayed on list and single pages (controlled by `Thumbnail.Visibility`)
- **Image generation**: AI-generated from `ImagePrompt` frontmatter field (currently manual, to be automated)

### Category Organization
Each category is a top-level section with its own list page. Homepage displays mixed category feeds using different article list styles for visual variety.

### Ad Integration
Google AdSense is integrated at multiple levels:
- **Mid-article**: Via `{{< articlead >}}` shortcode
- **Banner ads**: Via `ad-banner1.html` and `ad-banner2.html` partials
- **AdSense ID**: `ca-pub-5733732343388471`

## Critical Files

- [hugo.toml](hugo.toml) - Main site configuration
- [postcss.config.js](postcss.config.js) - CSS processing setup
- [themes/news/layouts/index.html](themes/news/layouts/index.html) - Homepage structure
- [themes/news/layouts/_default/single.html](themes/news/layouts/_default/single.html) - Article template
- [archetypes/default.md](archetypes/default.md) - Template for new content

## Notes
- The `mainroad` theme exists but is **not active** - only `news` theme is used
- The `agent/` directory is for future content automation (article generation, image creation, publishing pipeline)
- Site relies on external Hugo installation (not included in package.json)
