# CLAUDE.md — SalaciousNews Bedrock Flow Pipeline

Context for future Claude sessions working in this directory
(`/Users/codybeckner/Development/salaciousnews/bedrock-agent/`).

> For the full narrative writeup of how this pipeline evolved (Agent → Flow
> migration, single-commit publishing, image rendering fixes, dedup feature),
> see **`SOLUTION_NOTES.md`** in this same directory. This file is the quick
> orientation/reference card — read that one for the "why" and history.

---

## What this is

CDK app that deploys a **Bedrock Flow**-based pipeline which automatically
generates and publishes satirical tabloid articles to a Hugo static site
(`https://salacious.news`, repo `cbeckner/salaciousnews`) and cross-posts to
Instagram. Triggered on a schedule (currently running daily/multiple-times-daily).

AWS account: `281897100938`, region `us-east-1`, CLI profile `personal`.

---

## Quick commands (via Makefile)

```bash
make install   # create venv, install CDK deps
make synth     # cdk synth (no Docker needed)
make deploy    # cdk deploy (Docker REQUIRED — Lambda asset bundling)
make secrets   # push secrets from ../agent/.env into Secrets Manager
make invoke    # manually trigger the pipeline (invokes salaciousnews-trigger)
make clean     # cdk destroy (S3 bucket has RETAIN policy, survives)
```

All commands use `--profile personal --region us-east-1`.

---

## Architecture at a glance

```
trigger Lambda --(invokes Bedrock Flow via alias TSTALIASID)-->

FlowInputNode
  → FetchHeadlines      (news-actions)
  → PrepareArticles     (prepare-actions)   selection → DEDUP → scrape → rewrite → mark-seen
  → ArticleIterator     (fans out per selected article)
      → GenerateArticleImage  (image-actions, DALL·E mode)
      → GenerateSocialImage   (image-actions, PIL overlay mode)
      → BundleArticle         (bundle-article)
  → ResultCollector     (fans back in → collectedArray)
  → BatchPublish        (batch-publish — ONE GitHub commit for everything)
  → PostInstagram       (social-actions — DeepSeek ranks articles by viral
                          potential, posts the top 2 per run)
  → FlowOutputNode
```

Stack file: `stacks/salacious_agent_stack.py`
Lambda source dirs: `lambdas/{news_actions, prepare_actions, image_actions,
bundle_article, batch_publish, social_actions, trigger}`

> `lambdas/publish_actions/` still exists on disk but is **dead code** — it
> was replaced by `bundle_article` + `batch_publish` and removed from the CDK
> stack. Safe to delete if you're cleaning up, but harmless if left.

---

## Critical gotchas (read before touching anything)

### 1. Bedrock Flow expression syntax
All node connections MUST use `$.data` / `$.data.<key>` — NOT `$.<key>`.
Anything else throws "Expression must start with $.data".

### 2. Collector node requirements
Needs BOTH `arrayItem` AND `arraySize` inputs (wire `arraySize` from
`ArticleIterator.arraySize`). Its output must be named **`collectedArray`**
(NOT `collectorOutput`) or validation fails.

### 3. Lambda input shape when invoked from a Flow
Inputs arrive as `event["node"]["inputs"]` = `[{name, type, value}, ...]`,
**not** as flat top-level keys. Every handler has this helper — copy it if you
add a new Lambda:
```python
def _flow_inputs(event: dict) -> dict:
    raw = event.get("node", {}).get("inputs", [])
    if raw:
        return {inp["name"]: inp["value"] for inp in raw}
    return event  # direct invocation fallback
```

### 4. Flow alias — always use TSTALIASID
The trigger Lambda invokes the flow with `FLOW_ALIAS_ID = "TSTALIASID"` — a
reserved alias that always routes to **DRAFT**. This was a deliberate choice:
the installed boto3 (`1.43.24`) lacks `create_flow_version`/`update_flow_alias`,
so there's no easy way to publish versions and repoint a custom alias. Using
`TSTALIASID` means every `cdk deploy` takes effect immediately with no extra
alias-management step. Don't "fix" this by creating a custom alias unless you
also solve the boto3 version problem.

### 5. ⚠️ KNOWN BROKEN: image-actions Lambda bundling (x86_64 vs aarch64)
**Every `cdk deploy` currently breaks `image-actions`.** CDK's local pip
bundler runs on the dev Mac and produces a `pydantic_core` binary for the
host architecture (macOS/aarch64), but Lambda runs on `x86_64` Linux — causing
runtime import errors.

**Until this is fixed in CDK**, after every deploy you must manually rebuild
and push `image-actions`:
```bash
rm -rf /tmp/image_build && mkdir -p /tmp/image_build
docker run --rm --platform linux/amd64 \
  -v /tmp/image_build:/asset -v "$(pwd)/lambdas/image_actions":/src \
  public.ecr.aws/sam/build-python3.12 \
  bash -c "pip install -r /src/requirements.txt -t /asset -q && cp -r /src/* /asset/"
# verify the .so filename contains x86_64-linux-gnu:
find /tmp/image_build -name "*.so" | grep pydantic
cd /tmp/image_build && zip -r -q /tmp/image_actions.zip . && cd -
aws lambda update-function-code --function-name salaciousnews-image-actions \
  --zip-file fileb:///tmp/image_actions.zip --profile personal --region us-east-1
```
**Tracked as background task `task_fd003f9c`** — "Fix image-actions CDK
bundling for Linux x86_64". Suggested permanent fix: force Docker bundling in
CDK with `cdk.BundlingOptions(image=cdk.DockerImage.from_registry(...),
platform="linux/amd64", local=None)` so `cdk deploy` always builds correctly
without a manual follow-up step.

### 6. Secrets are cached per warm Lambda instance
Each Lambda keeps a module-level `_secret_cache: dict[str, str]`. After
rotating ANY secret (OpenAI key, GitHub token, Instagram token/user-id), you
must force a cold start or the Lambda keeps using the stale cached value:
```bash
aws lambda update-function-configuration --function-name <fn-name> \
  --environment "Variables={...,CACHE_BUST=$(date +%s)}" \
  --profile personal --region us-east-1
```
(Re-supply the full existing env var set, just add/change `CACHE_BUST`.)

---

## Key constants (in `stacks/salacious_agent_stack.py`)

```python
FOUNDATION_MODEL_ID = "deepseek.v3.2"
GITHUB_REPO         = "cbeckner/salaciousnews"   # NOT codybeckner — that 404s
SITE_BASE_URL       = "https://salacious.news"
```
`IMAGE_QUALITY` for `chatgpt-image-latest` must be one of `low|medium|high|auto`
(currently `"high"` — `"standard"` is rejected).

---

## Deduplication (DynamoDB)

Table: `salaciousnews-seen-urls` (partition key `url`, PAY_PER_REQUEST,
TTL attr `expires_at`, 90-day expiry, `RemovalPolicy.RETAIN`).

Flow in `prepare_actions/handler.py`:
1. Select 7 candidate URLs (buffer)
2. `_filter_seen_urls()` — `batch_get_item` against the table, drop already-seen
3. Take top 3 unseen → scrape → rewrite
4. `_mark_urls_seen()` — `batch_writer` writes used URLs with `expires_at = now + 90d`

Both dedup helpers fail **non-fatally** (log + continue without dedup) if
DynamoDB is unreachable — never blocks the pipeline.

Inspect state: `aws dynamodb scan --table-name salaciousnews-seen-urls --profile personal --region us-east-1`

> Caveat (accepted tradeoff): this only catches the *same URL* reused. The
> same underlying story from a *different* source will still pass through.

---

## Useful one-off commands

```bash
# Manually trigger a run
aws lambda invoke --function-name salaciousnews-trigger --payload '{}' \
  --profile personal --region us-east-1 /dev/stdout

# Tail a Lambda's recent logs
aws logs tail /aws/lambda/salaciousnews-prepare-actions --profile personal --region us-east-1 --since 30m

# Check a secret's current value (first chars only, to confirm it's not a placeholder)
aws secretsmanager get-secret-value --secret-id salaciousnews/openai-api-key \
  --profile personal --region us-east-1 --query SecretString --output text | cut -c1-15
```

---

## Status (as of 2026-06-07)

✅ Flow migration, single-commit publishing, title style, social image
rendering (sizing + em-dash font), and DynamoDB dedup are all **complete,
deployed, and verified live**.

⚠️ Only outstanding item: fix CDK bundling so `image-actions` survives a
normal `cdk deploy` without manual Docker rebuild (background task `task_fd003f9c`).
