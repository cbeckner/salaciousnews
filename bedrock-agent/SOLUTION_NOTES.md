# SalaciousNews — Bedrock Flow Pipeline: Solution Notes

> Snapshot of the architecture and the work completed in this session, migrating
> SalaciousNews from a Bedrock Agent to a Bedrock Flow, plus a series of
> follow-on fixes (single-commit publishing, social image rendering, and
> URL-based deduplication).

---

## 1. What SalaciousNews Is

An automated tabloid content pipeline that:
1. Fetches real news headlines
2. Picks a few "scandalous" candidates and rewrites them in a satirical tabloid voice (DeepSeek via Bedrock)
3. Generates an editorial header image (DALL·E / `chatgpt-image-latest` via OpenAI) and a square Instagram-style "social" image (PIL overlay on the header image)
4. Publishes the resulting Markdown + images to a GitHub repo (`cbeckner/salaciousnews`) which builds a static Hugo site at `https://salacious.news`
5. Cross-posts a teaser to Instagram

Runs on a schedule (originally every 3rd day, now daily / multiple times a day), triggered via a `salaciousnews-trigger` Lambda.

---

## 2. Architecture: Bedrock Agent → Bedrock Flow

### Why the change
The original implementation used a Bedrock **Agent** with action groups — opaque, hard to monitor, and it embedded model calls/config inside Lambdas in ways that were difficult to reason about as a pipeline. The user asked to rework it as a **Bedrock Flow**: an explicit, visual DAG of typed nodes that's easier to monitor and debug.

### The Flow DAG (CDK: `CfnFlow` in `stacks/salacious_agent_stack.py`)

```
FlowInputNode
   → FetchHeadlines        (Lambda: news-actions)
   → PrepareArticles       (Lambda: prepare-actions)   -- selection, dedup, scrape, rewrite
   → ArticleIterator       (Iterator node — fans out per article)
       → GenerateArticleImage  (Lambda: image-actions, "article image" mode)
       → GenerateSocialImage   (Lambda: image-actions, "social image" mode)
       → BundleArticle         (Lambda: bundle-article — packages per-item result)
   → ResultCollector       (Collector node — fans back in)
   → BatchPublish          (Lambda: batch-publish — single GitHub commit for everything)
   → PostInstagram         (Lambda: social-actions — posts once for the batch)
   → FlowOutputNode
```

### Hard-won Bedrock Flow lessons
- **Expression syntax**: All node I/O references must use `$.data` / `$.data.<key>` — NOT `$.<key>` or other JSONPath variants. (Spent significant effort tracking down "Expression must start with $.data" errors and mass-replacing with `Edit(replace_all=True)`.)
- **Collector node** requires BOTH an `arrayItem` input AND an `arraySize` input (wired from `ArticleIterator.arraySize`); its output must be named **`collectedArray`** (not `collectorOutput`).
- **Lambda invocation shape from a Flow**: inputs arrive as `event["node"]["inputs"]`, a list of `{name, type, value}` dicts — NOT as flat top-level event keys. Every Lambda handler now includes:
  ```python
  def _flow_inputs(event: dict) -> dict:
      raw = event.get("node", {}).get("inputs", [])
      if raw:
          return {inp["name"]: inp["value"] for inp in raw}
      return event  # direct invocation fallback
  ```
- **Aliases**: `TSTALIASID` is a reserved alias ID that always routes to a Flow's (or Agent's) **DRAFT** version. Because the boto3 version available (`1.43.24`) lacks `create_flow_version` / `update_flow_alias`, we standardized on invoking the Flow via `TSTALIASID` so the trigger Lambda always executes the latest DRAFT — no manual alias/version bumps needed after a CDK deploy. This is set via `FLOW_ALIAS_ID = "TSTALIASID"` in the trigger Lambda's environment (both live and in CDK source).
- **CFN LogGroup naming**: `_make_log_group(construct_id, log_suffix)` preserves the *original* CDK logical IDs (`News`, `Image`, `Publish`, `Social`, `Trigger`) and physical names (`news`, `image`, `publish`, `social`, `trigger`) to avoid "resource already exists" conflicts when migrating the stack in place.

### Lambda inventory (post-migration)
| Lambda | Role |
|---|---|
| `news-actions` | Fetches today's headlines |
| `prepare-actions` | Candidate selection → dedup filter → scrape → rewrite → mark-seen |
| `image-actions` | Dual-mode: generates DALL·E article image OR PIL social image overlay |
| `bundle-article` | NEW — tiny per-iteration packager: `{article, image_info, social_s3_key}` → feeds Collector |
| `batch-publish` | NEW — single-commit GitHub publish via the Git Trees API |
| `social-actions` | Posts once to Instagram using the first article in the batch that has a social image |
| `trigger` | Entry point; invokes the Flow via `TSTALIASID` |

`publish-actions` (the old per-article publisher) was **deleted** and replaced by `bundle-article` + `batch-publish`.

---

## 3. Fix: Single GitHub Commit Per Pipeline Run (was 2 commits/article)

**Problem**: image and content were committed separately, once per article — 3 articles meant 6 commits, each triggering a full Hugo rebuild.

**Chosen solution ("Option A")**: Use the **GitHub Git Trees API** to assemble *all* files (every article's image + Markdown) into a single atomic commit at the end of the run.

`lambdas/batch_publish/handler.py` (new) implements:
1. Get the branch HEAD ref → get the base tree SHA
2. Create a **blob** for each file (images + markdown, across all articles)
3. Create **one tree** referencing all new blobs
4. Create **one commit** pointing at that tree
5. **Update the branch ref** to the new commit

Returns `{articles: [...], commit_sha, files_committed}`. Verified live: commit `d4b6103b "content: publish 2 articles"` contained 4 files (2 images + 2 markdown) in a single commit/build trigger.

This required restructuring the Flow: per-article work (`GenerateArticleImage`, `GenerateSocialImage`, `BundleArticle`) happens inside the `ArticleIterator`, results are gathered by `ResultCollector` into `collectedArray`, and `BatchPublish` + `PostInstagram` run **once** after the loop, not per-item.

---

## 4. Fix: Article Title Style (DeepSeek → OpenAI-style headlines)

User compared DeepSeek's ALL-CAPS screaming headlines vs. OpenAI's punchier title-case style and preferred the latter. Updated the rewrite prompt in `prepare_actions/handler.py` (`_rewrite_articles`) with explicit **Title style rules**:
- Title case (not every word capitalized)
- Max 10 words
- No ALL CAPS — emphasis via word choice
- Lead with the scandalous detail, not the source
- Use an em-dash (—) for dramatic pivot, e.g. *"Stars Bail on Trump Concert—He Stars in It Himself"*
- "Think New York Post front page: one killer line"

---

## 5. Fix: Social Image Text Rendering

**Problem 1 — text was tiny/illegible.** Root cause: `_load_font` was looking for system TTF fonts at hardcoded Linux paths that don't exist in the Lambda runtime, silently falling through to `ImageFont.load_default()` (a tiny bitmap font).

**Fix**:
- Bundled `Roboto-Bold.ttf` directly inside the Lambda directory (`lambdas/image_actions/`), loaded via `Path(__file__).parent / "Roboto-Bold.ttf"`.
- Rewrote `_apply_gradient` to produce a black gradient fading in at 55% of image height and fully opaque by 72%, creating a solid dark "text zone" covering the bottom ~28%.
- Rewrote the text-sizing logic in `generate_social_image` to target that bottom band: auto-size font from **120px down to a 52px minimum** until the wrapped text fits, then vertically center it in the dark zone. Logo repositioned to sit just above the text band (max height 100px) with horizontal accent bars.

**Problem 2 — em-dash (—) didn't render.** Roboto-Bold lacked full Unicode coverage; the em-dash glyph was missing/invisible.

**Fix**:
- Bundled `NotoSans-Bold.ttf` (full Unicode coverage) and made it the **first** choice in `_load_font`'s candidate search order (Roboto kept as secondary fallback).
- Added punctuation normalization before word-wrapping: `title = title.replace("—", " — ").replace("  ", " ").strip()` so the em-dash is tokenized as its own "word" and wraps cleanly.

Both fixes were visually verified against user-provided screenshots — confirmed "Perfect. Thank you so much!"

Font search order in `_load_font` (in `lambdas/image_actions/handler.py`):
```
NotoSans-Bold.ttf (bundled) → Roboto-Bold.ttf (bundled) → /opt/fonts/... → various
system Linux paths → ImageFont.load_default(size=...)
```

---

## 6. Feature: URL-Based Deduplication (DynamoDB)

**Problem**: Running the pipeline daily (or multiple times/day) risked re-selecting and re-publishing the same source article. Static site, so state needs external storage.

**Design (approved by user as-is)**:
- New DynamoDB table `salaciousnews-seen-urls`:
  - Partition key: `url` (String)
  - Billing: `PAY_PER_REQUEST`
  - TTL attribute: `expires_at` (auto-expires entries after **90 days**, self-cleaning)
  - `RemovalPolicy.RETAIN`, point-in-time recovery disabled
- CDK changes in `stacks/salacious_agent_stack.py`:
  ```python
  seen_urls_table = dynamodb.Table(
      self, "SeenUrlsTable",
      table_name="salaciousnews-seen-urls",
      partition_key=dynamodb.Attribute(name="url", type=dynamodb.AttributeType.STRING),
      billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
      time_to_live_attribute="expires_at",
      removal_policy=RemovalPolicy.RETAIN,
      point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
          point_in_time_recovery_enabled=False,
      ),
  )
  ```
  - Granted `seen_urls_table.grant_read_write_data(prepare_role)`
  - Added env vars to `prepare-actions`: `SEEN_URLS_TABLE`, `SEEN_URL_TTL_DAYS=90`
  - Added `CfnOutput(self, "SeenUrlsTableName", ...)`

**Pipeline logic change (`lambdas/prepare_actions/handler.py`)**:
1. `_select_articles` now requests **7 candidates** (buffer) instead of hardcoded 3 — `num` parameter, default 7
2. `_filter_seen_urls(selections)` — batch-checks all candidate URLs against DynamoDB via `batch_get_item`, filters out any already seen; logs `"Dedup: skipped N already-seen URL(s)"`
3. Take the top 3 unseen candidates (falls back gracefully — if all 7 are seen, uses top 3 anyway with a warning; if fewer than 3 unseen, proceeds with what's available)
4. Scrape + rewrite as before
5. `_mark_urls_seen(used_urls)` — writes the URLs that were actually used to DynamoDB via `batch_writer`, each with `seen_at` (ISO timestamp) and `expires_at` (epoch seconds, now + 90 days)

Key helper functions added (full code preserved in `lambdas/prepare_actions/handler.py` lines ~176–235):
```python
def _get_seen_table(): ...
def _filter_seen_urls(selections: list[dict]) -> list[dict]: ...   # batch_get_item
def _mark_urls_seen(urls: list[str]) -> None: ...                   # batch_writer + TTL
```

Both helpers are defensive — DynamoDB read/write failures are logged and **non-fatal** (the pipeline proceeds without dedup rather than failing the run).

### Verification (live, two consecutive runs)
- **Run 1**: "Got 7 candidates" → "Using 3 unseen article(s)" → "Rewrote 2 articles" (one article was inaccessible) → "Marked 2 URL(s) as seen (TTL 90d)"
- **Run 2** (immediately after): "Got 7 candidates" → **"Dedup: skipped 1 already-seen URL(s)"** → "Using 3 unseen article(s)" → "Rewrote 2 articles" → "Marked 2 URL(s) as seen"
- Final `aws dynamodb scan` showed **4 unique URLs** total, each with a 90-day `expires_at`:
  - `apnews.com/article/china-humanoid-robots-ai-demand-...` (Run 1)
  - `washingtonpost.com/politics/2026/06/05/tech-leaders-...` (Run 1)
  - `axios.com/2026/06/05/stocks-nasdaq-tech-stocks` (Run 2)
  - `hollywoodreporter.com/.../taylor-swift-travis-kelce-wedding-...` (Run 2)

This confirms the overlapping URL between the two runs was correctly identified and skipped, and the table is functioning as designed (auto-expiring after 90 days via TTL, no manual cleanup needed).

> Note: this only prevents re-using the *same URL* — the same underlying story picked up from a *different* source would still pass the filter. That tradeoff was explicitly accepted by the user as "good enough."

---

## 7. Other Errors Encountered & Fixed Along the Way

1. **`pydantic_core` architecture mismatch (recurring)** — CDK's local pip bundler builds on macOS (host arch), but Lambda runs on `x86_64`. Each deploy required manually rebuilding `image-actions` with:
   ```
   docker run --rm --platform linux/amd64 -v ... public.ecr.aws/sam/build-python3.12 \
       bash -c "pip install -r requirements.txt -t /asset -q"
   ```
   then verifying the `.so` filename contains `x86_64-linux-gnu`, zipping, and `aws lambda update-function-code`.
   **⚠️ This is NOT yet permanently fixed** — flagged as background task `task_fd003f9c`: "Fix image-actions CDK bundling for Linux x86_64" (suggested approach: `cdk.BundlingOptions` with `image=cdk.DockerImage.from_registry(...)`, `platform="linux/amd64"`, `local=None`). **Every future `make deploy` will re-break `image-actions` until this is addressed.**

2. **Flow alias stuck on stale version** — Resolved by switching to `TSTALIASID` (routes directly to DRAFT), avoiding the need for `create_flow_version`/`update_flow_alias` (unsupported in the installed boto3).

3. **GitHub repo name typo** — CDK had `codybeckner/salaciousnews`; actual repo is `cbeckner/salaciousnews` (confirmed via GitHub API `/user` → `login: cbeckner`). Fixed in CDK constant `GITHUB_REPO` and live Lambda env var.

4. **GitHub PAT permissions (403)** — Fine-grained PAT lacked `Contents: write`; user updated permissions in GitHub UI. Required forcing a Lambda cold start (`update-function-configuration` with a `CACHE_BUST` timestamp env var) to bust the module-level `_secret_cache`.

5. **OpenAI secret had placeholder value** (`your_openai_api_key_here`) — found via `aws secretsmanager get-secret-value | cut -c1-15`; user replaced via console; required forcing cold starts again.

6. **`IMAGE_QUALITY: "standard"` invalid for `chatgpt-image-latest`** — model only supports `low | medium | high | auto`. Changed to `"high"` in CDK and live config.

---

## 8. Operational Notes / Gotchas for Future Maintenance

- **Secrets are cached per-Lambda-instance** in module-level `_secret_cache` dicts. After rotating any secret (OpenAI key, GitHub token, Instagram token), force a cold start: `aws lambda update-function-configuration --function-name <fn> --environment "Variables={...,CACHE_BUST=$(date +%s)}"`.
- **`TSTALIASID`** is the alias to invoke for the Flow — it always points at DRAFT, so CDK deploys take effect immediately without manual alias management.
- **Constants to know** (`stacks/salacious_agent_stack.py`):
  - `FOUNDATION_MODEL_ID = "deepseek.v3.2"`
  - `GITHUB_REPO = "cbeckner/salaciousnews"`
  - `SITE_BASE_URL = "https://salacious.news"`
- Trigger the pipeline manually: `aws lambda invoke --function-name salaciousnews-trigger ...`
- Inspect dedup state: `aws dynamodb scan --table-name salaciousnews-seen-urls`
- **Outstanding work**: background task `task_fd003f9c` — fix CDK Docker bundling for `image-actions` so deploys stop overwriting it with a broken macOS-arch `pydantic_core` binary.

---

## 9. Status Summary

✅ Bedrock Flow migration — complete, deployed, verified end-to-end
✅ Single-commit GitHub publishing — complete, verified (`d4b6103b`, 4 files / 1 commit)
✅ Title style update (title case, no ALL CAPS, em-dash pivots) — complete
✅ Social image text sizing — complete, visually verified
✅ Em-dash font rendering — complete, visually verified
✅ DynamoDB URL deduplication — complete, deployed, verified across 2 live runs (correctly skipped 1 duplicate)
⚠️ CDK Lambda bundling for `image-actions` (Linux x86_64) — **still broken**, manual rebuild required after every `cdk deploy`; tracked as background task `task_fd003f9c`
