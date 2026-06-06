# SalaciousNews Bedrock Agent — deployment helper
# Usage: make <target>
# Requires: AWS CLI with 'personal' profile, Docker (for cdk deploy), Python 3.12

PROFILE   := personal
REGION    := us-east-1
VENV      := .venv/bin
CDK       := cdk
ENV_FILE  := ../agent/.env

.PHONY: install bootstrap secrets deploy synth invoke clean

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
