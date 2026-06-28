"""
CDK stack for the SalaciousNews Bedrock Flow pipeline.

Resources created:
  - S3 bucket                 (image staging — posts/ and social/ prefixes)
  - Secrets Manager           (OpenAI key, NewsAPI key, GitHub token, Instagram creds)
  - Lambda functions:
      news-actions            fetches headlines from NewsAPI
      prepare-actions         selects + scrapes + rewrites via DeepSeek (calls Bedrock)
      image-actions           DALL-E article image + PIL social image
      bundle-article          per-article bundler (runs inside Iterator)
      batch-publish           commits ALL articles in ONE Git Trees API commit
      social-actions          posts to Instagram (runs once, after batch publish)
      trigger                 EventBridge → invoke_flow
  - Bedrock Flow              explicit pipeline DAG
  - Bedrock Flow Version      immutable snapshot
  - Bedrock Flow Alias        stable invoke target ("prod")
  - EventBridge Scheduler     daily trigger at 08:00 UTC
  - CloudWatch Alarms         Lambda errors + DLQ depth
  - SNS Topic                 alarm notifications
"""

import shutil
import subprocess
import sys
from pathlib import Path

import aws_cdk as cdk
import jsii
from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_bedrock as bedrock,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_scheduler as scheduler,
    aws_secretsmanager as sm,
    aws_sns as sns,
    aws_sqs as sqs,
)
from constructs import Construct

# ---------------------------------------------------------------------------
# Local bundler — installs Lambda deps via pip without Docker
# ---------------------------------------------------------------------------
@jsii.implements(cdk.ILocalBundling)
class LocalPipBundler:
    def __init__(self, source_dir: Path, extra_files: list[tuple[Path, str]] | None = None):
        self.source_dir = source_dir
        self.extra_files = extra_files or []

    def try_bundle(self, output_dir: str, _options: cdk.BundlingOptions) -> bool:
        out = Path(output_dir)
        try:
            req = self.source_dir / "requirements.txt"
            if req.exists():
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(req), "-t", str(out), "-q"],
                    check=True,
                )
            for item in self.source_dir.iterdir():
                if item.name in ("requirements.txt", "__pycache__"):
                    continue
                dest = out / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
            for src_path, dest_name in self.extra_files:
                if src_path.exists():
                    shutil.copy2(src_path, out / dest_name)
            return True
        except Exception as exc:
            print(f"[LocalPipBundler] Failed for {self.source_dir}: {exc}")
            return False


# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
LAMBDAS_DIR = ROOT / "lambdas"
ASSETS_DIR = ROOT / "assets"

FOUNDATION_MODEL_ID = "deepseek.v3.2"

GITHUB_REPO = "cbeckner/salaciousnews"
SITE_BASE_URL = "https://salacious.news"


class SalaciousAgentStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ------------------------------------------------------------------ #
        # S3 — image staging bucket                                           #
        # ------------------------------------------------------------------ #
        images_bucket = s3.Bucket(
            self, "ImagesBucket",
            bucket_name=f"salaciousnews-media-{self.account}",
            removal_policy=RemovalPolicy.RETAIN,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="expire-social-images",
                    prefix="social/",
                    expiration=Duration.days(7),
                ),
                s3.LifecycleRule(
                    id="expire-post-images",
                    prefix="posts/",
                    expiration=Duration.days(365),
                ),
            ],
        )

        # ------------------------------------------------------------------ #
        # DynamoDB — seen-URLs deduplication table                           #
        # ------------------------------------------------------------------ #
        seen_urls_table = dynamodb.Table(
            self, "SeenUrlsTable",
            table_name="salaciousnews-seen-urls",
            partition_key=dynamodb.Attribute(
                name="url",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=False,
            ),
        )

        # ------------------------------------------------------------------ #
        # Secrets Manager                                                     #
        # ------------------------------------------------------------------ #
        openai_secret = sm.Secret(
            self, "OpenAISecret",
            secret_name="salaciousnews/openai-api-key",
            description="OpenAI API key for DALL-E image generation",
        )
        newsapi_secret = sm.Secret(
            self, "NewsApiSecret",
            secret_name="salaciousnews/newsapi-key",
            description="NewsAPI.org API key",
        )
        github_token_secret = sm.Secret(
            self, "GitHubTokenSecret",
            secret_name="salaciousnews/github-token",
            description="GitHub fine-grained PAT (contents:write on the repo)",
        )
        instagram_token_secret = sm.Secret(
            self, "InstagramTokenSecret",
            secret_name="salaciousnews/instagram-access-token",
            description="Instagram Graph API long-lived access token",
        )
        instagram_user_id_secret = sm.Secret(
            self, "InstagramUserIdSecret",
            secret_name="salaciousnews/instagram-user-id",
            description="Instagram Business Account user ID",
        )

        # ------------------------------------------------------------------ #
        # SNS — alarm notifications                                           #
        # ------------------------------------------------------------------ #
        alarm_topic = sns.Topic(
            self, "AlarmTopic",
            topic_name="salaciousnews-pipeline-alarms",
            display_name="SalaciousNews Pipeline Alarms",
        )

        # ------------------------------------------------------------------ #
        # Helpers                                                             #
        # ------------------------------------------------------------------ #
        def _make_log_group(construct_id: str, log_suffix: str) -> logs.LogGroup:
            """
            construct_id: CDK construct ID — must match existing stack to avoid CFN conflicts.
            log_suffix:   suffix after /aws/lambda/salaciousnews-
            """
            return logs.LogGroup(
                self, f"{construct_id}LogGroup",
                log_group_name=f"/aws/lambda/salaciousnews-{log_suffix}",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY,
            )

        def _make_lambda_role(name: str) -> iam.Role:
            return iam.Role(
                self, f"{name}Role",
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name(
                        "service-role/AWSLambdaBasicExecutionRole"
                    )
                ],
            )

        def _make_dlq(name: str) -> sqs.Queue:
            return sqs.Queue(
                self, f"{name}Dlq",
                queue_name=f"salaciousnews-{name.lower()}-dlq",
                retention_period=Duration.days(14),
                encryption=sqs.QueueEncryption.SQS_MANAGED,
            )

        def _add_error_alarm(fn: lambda_.Function, fn_name: str):
            alarm = cw.Alarm(
                self, f"{fn_name}ErrorAlarm",
                metric=fn.metric_errors(period=Duration.minutes(5)),
                threshold=1,
                evaluation_periods=1,
                alarm_description=f"{fn_name} Lambda error",
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
            alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))

        def _add_dlq_alarm(dlq: sqs.Queue, name: str):
            alarm = cw.Alarm(
                self, f"{name}DlqAlarm",
                metric=dlq.metric_approximate_number_of_messages_visible(
                    period=Duration.minutes(5)
                ),
                threshold=1,
                evaluation_periods=1,
                alarm_description=f"{name} DLQ has messages",
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
            alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))

        def _bundling(source_dir: Path,
                      extra_files: list[tuple[Path, str]] | None = None) -> cdk.BundlingOptions:
            return cdk.BundlingOptions(
                image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                local=LocalPipBundler(source_dir, extra_files),
                command=[
                    "bash", "-c",
                    "pip install -r requirements.txt -t /asset-output -q && cp -r . /asset-output",
                ],
            )

        # ------------------------------------------------------------------ #
        # Lambda: news-actions  (fetch headlines from NewsAPI)               #
        # ------------------------------------------------------------------ #
        news_role = _make_lambda_role("NewsActions")
        newsapi_secret.grant_read(news_role)
        news_dlq = _make_dlq("news-actions")

        news_lambda = lambda_.Function(
            self, "NewsActionsLambda",
            function_name="salaciousnews-news-actions",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                str(LAMBDAS_DIR / "news_actions"),
                bundling=_bundling(LAMBDAS_DIR / "news_actions"),
            ),
            role=news_role,
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "NEWS_API_KEY_SECRET": newsapi_secret.secret_name,
                "ARTICLE_MIN_LENGTH": "300",
            },
            dead_letter_queue=news_dlq,
            log_group=_make_log_group("News", "news"),
        )
        _add_error_alarm(news_lambda, "NewsActions")
        _add_dlq_alarm(news_dlq, "NewsActions")

        # ------------------------------------------------------------------ #
        # Lambda: prepare-actions  (select + scrape + rewrite via DeepSeek) #
        # ------------------------------------------------------------------ #
        prepare_role = _make_lambda_role("PrepareActions")
        prepare_role.add_to_policy(iam.PolicyStatement(
            sid="InvokeDeepSeek",
            actions=["bedrock:InvokeModel", "bedrock:Converse"],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/{FOUNDATION_MODEL_ID}",
            ],
        ))
        seen_urls_table.grant_read_write_data(prepare_role)
        prepare_dlq = _make_dlq("prepare-actions")

        prepare_lambda = lambda_.Function(
            self, "PrepareActionsLambda",
            function_name="salaciousnews-prepare-actions",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                str(LAMBDAS_DIR / "prepare_actions"),
                bundling=_bundling(LAMBDAS_DIR / "prepare_actions"),
            ),
            role=prepare_role,
            # Scraping 3 URLs + 2 DeepSeek calls can take a few minutes
            timeout=Duration.minutes(8),
            memory_size=512,
            environment={
                "FOUNDATION_MODEL_ID": FOUNDATION_MODEL_ID,
                "ARTICLE_MIN_LENGTH": "300",
                "SEEN_URLS_TABLE": seen_urls_table.table_name,
                "SEEN_URL_TTL_DAYS": "90",
            },
            dead_letter_queue=prepare_dlq,
            log_group=_make_log_group("PrepareActions", "prepare-actions"),
        )
        _add_error_alarm(prepare_lambda, "PrepareActions")
        _add_dlq_alarm(prepare_dlq, "PrepareActions")

        # ------------------------------------------------------------------ #
        # Lambda: image-actions  (DALL-E + PIL)                              #
        # Must be built for Linux — pydantic_core has a compiled extension.  #
        # Use Docker bundling (image=) and set local=None.                   #
        # ------------------------------------------------------------------ #
        image_role = _make_lambda_role("ImageActions")
        openai_secret.grant_read(image_role)
        images_bucket.grant_put(image_role)
        images_bucket.grant_read(image_role)
        image_dlq = _make_dlq("image-actions")

        image_lambda = lambda_.Function(
            self, "ImageActionsLambda",
            function_name="salaciousnews-image-actions",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                str(LAMBDAS_DIR / "image_actions"),
                bundling=cdk.BundlingOptions(
                    image=cdk.DockerImage.from_registry("public.ecr.aws/sam/build-python3.12"),
                    local=None,  # force Docker — aarch64 pydantic_core breaks on Lambda x86
                    platform="linux/amd64",
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output -q && "
                        "cp -r . /asset-output && "
                        "cp /asset-input/logo.webp /asset-output/logo.webp 2>/dev/null || true",
                    ],
                ),
            ),
            role=image_role,
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "OPENAI_API_KEY_SECRET": openai_secret.secret_name,
                "IMAGES_BUCKET": images_bucket.bucket_name,
                "IMAGE_SIZE": "1536x1024",
                "IMAGE_QUALITY": "high",
                "OPENAI_IMAGE_MODEL": "chatgpt-image-latest",
            },
            dead_letter_queue=image_dlq,
            log_group=_make_log_group("Image", "image"),
        )
        _add_error_alarm(image_lambda, "ImageActions")
        _add_dlq_alarm(image_dlq, "ImageActions")

        # ------------------------------------------------------------------ #
        # Lambda: bundle-article  (per-article bundler, runs in Iterator)   #
        # ------------------------------------------------------------------ #
        bundle_role = _make_lambda_role("BundleArticle")
        bundle_dlq = _make_dlq("bundle-article")

        bundle_lambda = lambda_.Function(
            self, "BundleArticleLambda",
            function_name="salaciousnews-bundle-article",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                str(LAMBDAS_DIR / "bundle_article"),
                bundling=_bundling(LAMBDAS_DIR / "bundle_article"),
            ),
            role=bundle_role,
            timeout=Duration.seconds(10),
            memory_size=128,
            dead_letter_queue=bundle_dlq,
            log_group=_make_log_group("BundleArticle", "bundle-article"),
        )
        _add_error_alarm(bundle_lambda, "BundleArticle")
        _add_dlq_alarm(bundle_dlq, "BundleArticle")

        # ------------------------------------------------------------------ #
        # Lambda: batch-publish  (one Trees API commit for all articles)     #
        # ------------------------------------------------------------------ #
        batch_publish_role = _make_lambda_role("BatchPublish")
        github_token_secret.grant_read(batch_publish_role)
        images_bucket.grant_read(batch_publish_role)
        batch_publish_dlq = _make_dlq("batch-publish")

        batch_publish_lambda = lambda_.Function(
            self, "BatchPublishLambda",
            function_name="salaciousnews-batch-publish",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                str(LAMBDAS_DIR / "batch_publish"),
                bundling=_bundling(LAMBDAS_DIR / "batch_publish"),
            ),
            role=batch_publish_role,
            # 3 articles × 2 blob uploads + tree + commit = ~10 API calls; give headroom
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "GITHUB_TOKEN_SECRET": github_token_secret.secret_name,
                "IMAGES_BUCKET": images_bucket.bucket_name,
                "GITHUB_REPO": GITHUB_REPO,
                "GITHUB_BRANCH": "main",
                "SITE_BASE_URL": SITE_BASE_URL,
            },
            dead_letter_queue=batch_publish_dlq,
            log_group=_make_log_group("BatchPublish", "batch-publish"),
        )
        _add_error_alarm(batch_publish_lambda, "BatchPublish")
        _add_dlq_alarm(batch_publish_dlq, "BatchPublish")

        # ------------------------------------------------------------------ #
        # Lambda: social-actions  (post to Instagram)                        #
        # ------------------------------------------------------------------ #
        social_role = _make_lambda_role("SocialActions")
        instagram_token_secret.grant_read(social_role)
        instagram_user_id_secret.grant_read(social_role)
        images_bucket.grant_read(social_role)
        social_role.add_to_policy(iam.PolicyStatement(
            sid="InvokeBedrockForViralRanking",
            actions=["bedrock:InvokeModel", "bedrock:Converse"],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/{FOUNDATION_MODEL_ID}",
            ],
        ))
        social_dlq = _make_dlq("social-actions")

        social_lambda = lambda_.Function(
            self, "SocialActionsLambda",
            function_name="salaciousnews-social-actions",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                str(LAMBDAS_DIR / "social_actions"),
                bundling=_bundling(LAMBDAS_DIR / "social_actions"),
            ),
            role=social_role,
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "INSTAGRAM_TOKEN_SECRET": instagram_token_secret.secret_name,
                "INSTAGRAM_USER_ID_SECRET": instagram_user_id_secret.secret_name,
                "IMAGES_BUCKET": images_bucket.bucket_name,
                "SITE_BASE_URL": SITE_BASE_URL,
                "FOUNDATION_MODEL_ID": FOUNDATION_MODEL_ID,
            },
            dead_letter_queue=social_dlq,
            log_group=_make_log_group("Social", "social"),
        )
        _add_error_alarm(social_lambda, "SocialActions")
        _add_dlq_alarm(social_dlq, "SocialActions")

        # ------------------------------------------------------------------ #
        # Bedrock Flow — execution role                                       #
        # ------------------------------------------------------------------ #
        flow_role = iam.Role(
            self, "BedrockFlowRole",
            role_name="salaciousnews-bedrock-flow-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("bedrock.amazonaws.com"),
            ),
            description="Execution role for the SalaciousNews Bedrock Flow",
        )
        # The flow invokes each Lambda node
        for fn in [news_lambda, prepare_lambda, image_lambda,
                   bundle_lambda, batch_publish_lambda, social_lambda]:
            fn.grant_invoke(flow_role)

        # ------------------------------------------------------------------ #
        # Bedrock Flow — grant each Lambda permission to be invoked by Flows  #
        # ------------------------------------------------------------------ #
        for fn, name in [
            (news_lambda,          "NewsActions"),
            (prepare_lambda,       "PrepareActions"),
            (image_lambda,         "ImageActions"),
            (bundle_lambda,        "BundleArticle"),
            (batch_publish_lambda, "BatchPublish"),
            (social_lambda,        "SocialActions"),
        ]:
            lambda_.CfnPermission(
                self, f"BedrockFlowInvoke{name}",
                action="lambda:InvokeFunction",
                function_name=fn.function_name,
                principal="bedrock.amazonaws.com",
                # Source ARN restricted to this account's flows
                source_arn=f"arn:aws:bedrock:{self.region}:{self.account}:flow/*",
            )

        # ------------------------------------------------------------------ #
        # Bedrock Flow definition                                             #
        # ------------------------------------------------------------------ #
        #
        # Pipeline graph:
        #
        #   FlowInputNode
        #       │
        #   FetchHeadlines (news-actions)
        #       │ headlines[]
        #   PrepareArticles (prepare-actions, calls DeepSeek)
        #       │ articles[]
        #   ArticleIterator ─── per article ──────────────────────────┐
        #       │ arrayItem                                            │
        #   GenerateArticleImage (image-actions / DALL-E)             │
        #       │                                                      │
        #   GenerateSocialImage  (image-actions / PIL overlay)        │
        #       │                                                      │
        #   BundleArticle ◄────────────── article ────────────────────┘
        #       │ {article, image_info, social_s3_key}
        #   ResultCollector
        #       │ [{article, image_info, social_s3_key}, ...]  ← full array
        #   BatchPublish  (ONE Trees API commit — 1 build trigger per run)
        #       │ {articles: [{article_url, title, teaser, social_s3_key}...]}
        #   PostInstagram (social-actions, posts once for the top article)
        #       │
        #   FlowOutputNode
        #
        # ------------------------------------------------------------------ #

        flow = bedrock.CfnFlow(
            self, "SalaciousFlow",
            name="salaciousnews-flow",
            description="SalaciousNews automated content pipeline",
            execution_role_arn=flow_role.role_arn,
            definition=bedrock.CfnFlow.FlowDefinitionProperty(
                nodes=[
                    # ── Input ────────────────────────────────────────────────
                    bedrock.CfnFlow.FlowNodeProperty(
                        name="FlowInputNode",
                        type="Input",
                        outputs=[
                            bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="document",
                                type="Object",
                            )
                        ],
                    ),
                    # ── FetchHeadlines ────────────────────────────────────────
                    bedrock.CfnFlow.FlowNodeProperty(
                        name="FetchHeadlines",
                        type="LambdaFunction",
                        configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            lambda_function=bedrock.CfnFlow.LambdaFunctionFlowNodeConfigurationProperty(
                                lambda_arn=news_lambda.function_arn,
                            )
                        ),
                        inputs=[
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="trigger",
                                type="Object",
                                expression="$.data",
                            )
                        ],
                        outputs=[
                            bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="functionResponse",
                                type="Object",
                            )
                        ],
                    ),
                    # ── PrepareArticles ───────────────────────────────────────
                    bedrock.CfnFlow.FlowNodeProperty(
                        name="PrepareArticles",
                        type="LambdaFunction",
                        configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            lambda_function=bedrock.CfnFlow.LambdaFunctionFlowNodeConfigurationProperty(
                                lambda_arn=prepare_lambda.function_arn,
                            )
                        ),
                        inputs=[
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="headlines",
                                type="Array",
                                expression="$.data.headlines",
                            )
                        ],
                        outputs=[
                            bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="functionResponse",
                                type="Object",
                            )
                        ],
                    ),
                    # ── ArticleIterator ───────────────────────────────────────
                    bedrock.CfnFlow.FlowNodeProperty(
                        name="ArticleIterator",
                        type="Iterator",
                        inputs=[
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="array",
                                type="Array",
                                expression="$.data.articles",
                            )
                        ],
                        outputs=[
                            bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="arrayItem",
                                type="Object",
                            ),
                            bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="arraySize",
                                type="Number",
                            ),
                        ],
                    ),
                    # ── GenerateArticleImage ──────────────────────────────────
                    bedrock.CfnFlow.FlowNodeProperty(
                        name="GenerateArticleImage",
                        type="LambdaFunction",
                        configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            lambda_function=bedrock.CfnFlow.LambdaFunctionFlowNodeConfigurationProperty(
                                lambda_arn=image_lambda.function_arn,
                            )
                        ),
                        inputs=[
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="article",
                                type="Object",
                                expression="$.data",
                            )
                        ],
                        outputs=[
                            bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="functionResponse",
                                type="Object",
                            )
                        ],
                    ),
                    # ── GenerateSocialImage ───────────────────────────────────
                    bedrock.CfnFlow.FlowNodeProperty(
                        name="GenerateSocialImage",
                        type="LambdaFunction",
                        configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            lambda_function=bedrock.CfnFlow.LambdaFunctionFlowNodeConfigurationProperty(
                                lambda_arn=image_lambda.function_arn,
                            )
                        ),
                        inputs=[
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="article",
                                type="Object",
                                expression="$.data",
                            ),
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="article_image_s3_key",
                                type="String",
                                expression="$.data.s3_key",
                            ),
                        ],
                        outputs=[
                            bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="functionResponse",
                                type="Object",
                            )
                        ],
                    ),
                    # ── BundleArticle ─────────────────────────────────────────
                    # Collects per-article outputs into one object for Collector
                    bedrock.CfnFlow.FlowNodeProperty(
                        name="BundleArticle",
                        type="LambdaFunction",
                        configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            lambda_function=bedrock.CfnFlow.LambdaFunctionFlowNodeConfigurationProperty(
                                lambda_arn=bundle_lambda.function_arn,
                            )
                        ),
                        inputs=[
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="article",
                                type="Object",
                                expression="$.data",
                            ),
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="image_info",
                                type="Object",
                                expression="$.data",
                            ),
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="social_s3_key",
                                type="String",
                                expression="$.data.s3_key",
                            ),
                        ],
                        outputs=[
                            bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="functionResponse",
                                type="Object",
                            )
                        ],
                    ),
                    # ── ResultCollector ───────────────────────────────────────
                    bedrock.CfnFlow.FlowNodeProperty(
                        name="ResultCollector",
                        type="Collector",
                        inputs=[
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="arrayItem",
                                type="Object",
                                expression="$.data",
                            ),
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="arraySize",
                                type="Number",
                                expression="$.data",
                            ),
                        ],
                        outputs=[
                            bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="collectedArray",
                                type="Array",
                            )
                        ],
                    ),
                    # ── BatchPublish ──────────────────────────────────────────
                    # ONE commit for all articles via GitHub Trees API
                    bedrock.CfnFlow.FlowNodeProperty(
                        name="BatchPublish",
                        type="LambdaFunction",
                        configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            lambda_function=bedrock.CfnFlow.LambdaFunctionFlowNodeConfigurationProperty(
                                lambda_arn=batch_publish_lambda.function_arn,
                            )
                        ),
                        inputs=[
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="articles_bundle",
                                type="Array",
                                expression="$.data",
                            )
                        ],
                        outputs=[
                            bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="functionResponse",
                                type="Object",
                            )
                        ],
                    ),
                    # ── PostInstagram ─────────────────────────────────────────
                    # Runs once after batch publish; picks the top article
                    bedrock.CfnFlow.FlowNodeProperty(
                        name="PostInstagram",
                        type="LambdaFunction",
                        configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                            lambda_function=bedrock.CfnFlow.LambdaFunctionFlowNodeConfigurationProperty(
                                lambda_arn=social_lambda.function_arn,
                            )
                        ),
                        inputs=[
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="batch_result",
                                type="Object",
                                expression="$.data",
                            ),
                        ],
                        outputs=[
                            bedrock.CfnFlow.FlowNodeOutputProperty(
                                name="functionResponse",
                                type="Object",
                            )
                        ],
                    ),
                    # ── Output ────────────────────────────────────────────────
                    bedrock.CfnFlow.FlowNodeProperty(
                        name="FlowOutputNode",
                        type="Output",
                        inputs=[
                            bedrock.CfnFlow.FlowNodeInputProperty(
                                name="document",
                                type="Object",
                                expression="$.data",
                            )
                        ],
                    ),
                ],
                connections=[
                    # FlowInputNode → FetchHeadlines
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="InputToFetchHeadlines",
                        source="FlowInputNode",
                        target="FetchHeadlines",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="document",
                                target_input="trigger",
                            )
                        ),
                    ),
                    # FetchHeadlines → PrepareArticles
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="FetchToPrepareFull",
                        source="FetchHeadlines",
                        target="PrepareArticles",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="functionResponse",
                                target_input="headlines",
                            )
                        ),
                    ),
                    # PrepareArticles → ArticleIterator
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="PrepareToIterator",
                        source="PrepareArticles",
                        target="ArticleIterator",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="functionResponse",
                                target_input="array",
                            )
                        ),
                    ),
                    # ArticleIterator → GenerateArticleImage
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="IteratorToGenerateImage",
                        source="ArticleIterator",
                        target="GenerateArticleImage",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="arrayItem",
                                target_input="article",
                            )
                        ),
                    ),
                    # ArticleIterator → GenerateSocialImage
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="IteratorToSocialImage",
                        source="ArticleIterator",
                        target="GenerateSocialImage",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="arrayItem",
                                target_input="article",
                            )
                        ),
                    ),
                    # ArticleIterator → BundleArticle (article passthrough)
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="IteratorToBundler",
                        source="ArticleIterator",
                        target="BundleArticle",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="arrayItem",
                                target_input="article",
                            )
                        ),
                    ),
                    # GenerateArticleImage → GenerateSocialImage (s3_key for overlay)
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="GenerateImageToSocial",
                        source="GenerateArticleImage",
                        target="GenerateSocialImage",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="functionResponse",
                                target_input="article_image_s3_key",
                            )
                        ),
                    ),
                    # GenerateArticleImage → BundleArticle (image_info)
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="GenerateImageToBundler",
                        source="GenerateArticleImage",
                        target="BundleArticle",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="functionResponse",
                                target_input="image_info",
                            )
                        ),
                    ),
                    # GenerateSocialImage → BundleArticle (social_s3_key)
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="SocialImageToBundler",
                        source="GenerateSocialImage",
                        target="BundleArticle",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="functionResponse",
                                target_input="social_s3_key",
                            )
                        ),
                    ),
                    # BundleArticle → ResultCollector
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="BundlerToCollector",
                        source="BundleArticle",
                        target="ResultCollector",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="functionResponse",
                                target_input="arrayItem",
                            )
                        ),
                    ),
                    # ArticleIterator.arraySize → ResultCollector.arraySize
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="IteratorSizeToCollector",
                        source="ArticleIterator",
                        target="ResultCollector",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="arraySize",
                                target_input="arraySize",
                            )
                        ),
                    ),
                    # ResultCollector → BatchPublish (full array)
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="CollectorToBatchPublish",
                        source="ResultCollector",
                        target="BatchPublish",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="collectedArray",
                                target_input="articles_bundle",
                            )
                        ),
                    ),
                    # BatchPublish → PostInstagram
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="BatchPublishToInstagram",
                        source="BatchPublish",
                        target="PostInstagram",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="functionResponse",
                                target_input="batch_result",
                            )
                        ),
                    ),
                    # PostInstagram → FlowOutput
                    bedrock.CfnFlow.FlowConnectionProperty(
                        name="InstagramToOutput",
                        source="PostInstagram",
                        target="FlowOutputNode",
                        type="Data",
                        configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                            data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                                source_output="functionResponse",
                                target_input="document",
                            )
                        ),
                    ),
                ],
            ),
        )

        # ------------------------------------------------------------------ #
        # Bedrock Flow Version (immutable snapshot) + Alias                  #
        # ------------------------------------------------------------------ #
        flow_version = bedrock.CfnFlowVersion(
            self, "SalaciousFlowVersion",
            flow_arn=flow.attr_arn,
            description="Initial production version",
        )
        flow_version.add_dependency(flow)

        flow_alias = bedrock.CfnFlowAlias(
            self, "SalaciousFlowAlias",
            flow_arn=flow.attr_arn,
            name="prod",
            description="Production alias",
            routing_configuration=[
                bedrock.CfnFlowAlias.FlowAliasRoutingConfigurationListItemProperty(
                    flow_version=flow_version.attr_version,
                )
            ],
        )
        flow_alias.add_dependency(flow_version)

        # ------------------------------------------------------------------ #
        # Lambda: trigger  (EventBridge → invoke_flow)                       #
        # ------------------------------------------------------------------ #
        trigger_role = _make_lambda_role("Trigger")
        trigger_role.add_to_policy(iam.PolicyStatement(
            sid="InvokeBedrockFlow",
            actions=["bedrock:InvokeFlow"],
            resources=[
                flow.attr_arn,
                f"arn:aws:bedrock:{self.region}:{self.account}:flow/{flow.attr_id}/alias/*",
            ],
        ))
        trigger_dlq = _make_dlq("trigger")

        trigger_lambda = lambda_.Function(
            self, "TriggerLambda",
            function_name="salaciousnews-trigger",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                str(LAMBDAS_DIR / "trigger"),
                bundling=_bundling(LAMBDAS_DIR / "trigger"),
            ),
            role=trigger_role,
            timeout=Duration.minutes(14),
            memory_size=256,
            environment={
                "FLOW_ID": flow.attr_id,
                # TSTALIASID always routes to DRAFT — safe for development.
                # After promoting to production, swap to: flow_alias.attr_id
                "FLOW_ALIAS_ID": "TSTALIASID",
            },
            dead_letter_queue=trigger_dlq,
            log_group=_make_log_group("Trigger", "trigger"),
        )
        _add_error_alarm(trigger_lambda, "Trigger")
        _add_dlq_alarm(trigger_dlq, "Trigger")

        # ------------------------------------------------------------------ #
        # EventBridge Scheduler — IAM role + schedule                        #
        # ------------------------------------------------------------------ #
        scheduler_role = iam.Role(
            self, "SchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
        )
        trigger_lambda.grant_invoke(scheduler_role)

        scheduler.CfnSchedule(
            self, "DailySchedule",
            name="salaciousnews-daily-pipeline",
            description="Triggers the SalaciousNews content pipeline daily at 08:00 UTC",
            schedule_expression="cron(0 8 * * ? *)",
            schedule_expression_timezone="UTC",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="FLEXIBLE",
                maximum_window_in_minutes=30,
            ),
            target=scheduler.CfnSchedule.TargetProperty(
                arn=trigger_lambda.function_arn,
                role_arn=scheduler_role.role_arn,
                retry_policy=scheduler.CfnSchedule.RetryPolicyProperty(
                    maximum_retry_attempts=2,
                    maximum_event_age_in_seconds=3600,
                ),
            ),
            state="ENABLED",
        )

        # ------------------------------------------------------------------ #
        # Outputs                                                             #
        # ------------------------------------------------------------------ #
        cdk.CfnOutput(self, "SeenUrlsTableName", value=seen_urls_table.table_name,
                      description="DynamoDB table storing processed article URLs (dedup)")
        cdk.CfnOutput(self, "FlowId", value=flow.attr_id, description="Bedrock Flow ID")
        cdk.CfnOutput(self, "FlowAliasId", value=flow_alias.attr_id,
                      description="Bedrock Flow Alias ID (prod)")
        cdk.CfnOutput(self, "TriggerLambdaName", value=trigger_lambda.function_name,
                      description="Invoke this Lambda to run the pipeline manually")
        cdk.CfnOutput(self, "ImagesBucketName", value=images_bucket.bucket_name)
        cdk.CfnOutput(self, "AlarmTopicArn", value=alarm_topic.topic_arn,
                      description="Subscribe your email here for pipeline failure alerts")
