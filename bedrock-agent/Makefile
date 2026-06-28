# SalaciousNews Bedrock Agent — deployment helper
# Usage: make <target>
# Requires: AWS CLI with 'personal' profile, Docker (for cdk deploy), Python 3.12

PROFILE   := personal
REGION    := us-east-1
VENV      := .venv/bin
CDK       := cdk
ENV_FILE  := ../agent/.env

# S3 key of an existing social image for test-instagram (override on CLI)
TEST_SOCIAL_S3_KEY ?= social/test.png
TEST_CAPTION       ?= Test post from Salacious News
TEST_ARTICLE_URL   ?= https://salacious.news/

.PHONY: install bootstrap secrets deploy synth invoke test-instagram clean

## Install Python CDK dependencies
install:
	python3 -m venv .venv
	$(VENV)/pip install -q -r requirements.txt

## Bootstrap CDK in the account/region (run once)
bootstrap:
	source .venv/bin/activate && \
	JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 \
	$(CDK) bootstrap aws://281897100938/$(REGION) --profile $(PROFILE)

## Synthesize CloudFormation (no Docker needed)
synth:
	source .venv/bin/activate && \
	JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 \
	$(CDK) synth --profile $(PROFILE) --no-asset-metadata

## Deploy the full stack (Docker must be running for Lambda bundling)
deploy:
	source .venv/bin/activate && \
	JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 \
	$(CDK) deploy --profile $(PROFILE) --require-approval never

## Populate Secrets Manager with values from ../agent/.env
secrets:
	@echo "Populating Secrets Manager from $(ENV_FILE)..."
	@set -a; source $(ENV_FILE); set +a; \
	aws secretsmanager put-secret-value \
		--secret-id salaciousnews/openai-api-key \
		--secret-string "$$OPENAI_API_KEY" \
		--profile $(PROFILE) --region $(REGION) --output text --query VersionId; \
	aws secretsmanager put-secret-value \
		--secret-id salaciousnews/newsapi-key \
		--secret-string "$$NEWS_API_KEY" \
		--profile $(PROFILE) --region $(REGION) --output text --query VersionId; \
	aws secretsmanager put-secret-value \
		--secret-id salaciousnews/github-token \
		--secret-string "$$GITHUB_TOKEN" \
		--profile $(PROFILE) --region $(REGION) --output text --query VersionId; \
	aws secretsmanager put-secret-value \
		--secret-id salaciousnews/instagram-access-token \
		--secret-string "$$INSTAGRAM_ACCESS_TOKEN" \
		--profile $(PROFILE) --region $(REGION) --output text --query VersionId; \
	aws secretsmanager put-secret-value \
		--secret-id salaciousnews/instagram-user-id \
		--secret-string "$$INSTAGRAM_USER_ID" \
		--profile $(PROFILE) --region $(REGION) --output text --query VersionId
	@echo "Done."

## Invoke social_actions Lambda directly — no Flow, no image generation.
## Override defaults on the CLI, e.g.:
##   make test-instagram TEST_SOCIAL_S3_KEY=social/my-image.png TEST_CAPTION="Hello world"
test-instagram:
	@PAYLOAD=$$(printf '{"batch_result":{"articles":[{"social_s3_key":"%s","article_url":"%s","teaser":"%s","slug":"test","title":"Test"}]}}' \
		"$(TEST_SOCIAL_S3_KEY)" "$(TEST_ARTICLE_URL)" "$(TEST_CAPTION)"); \
	echo "Invoking salaciousnews-social-actions with payload:"; \
	echo "$$PAYLOAD" | python3 -m json.tool; \
	aws lambda invoke \
		--function-name salaciousnews-social-actions \
		--cli-binary-format raw-in-base64-out \
		--payload "$$PAYLOAD" \
		--log-type Tail \
		--profile $(PROFILE) --region $(REGION) \
		--query 'LogResult' --output text \
		/tmp/social_test_response.json | base64 -d; \
	echo; echo "Response:"; cat /tmp/social_test_response.json; echo

## Manually invoke the pipeline (triggers the trigger Lambda, which calls the agent)
invoke:
	aws lambda invoke \
		--function-name salaciousnews-trigger \
		--payload '{}' \
		--log-type Tail \
		--profile $(PROFILE) --region $(REGION) \
		/dev/stdout

## Destroy all stack resources (leaves S3 bucket with RETAIN policy)
clean:
	source .venv/bin/activate && \
	JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 \
	$(CDK) destroy --profile $(PROFILE) --force
