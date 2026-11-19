#!/bin/sh
# Packages and deploys the medquest-kb-chat-v2 Lambda (creates it if missing).
#
#   sh lambda/v2/deploy.sh
#
# Needs AWS credentials and a fresh `python3 loader/build.py`.
set -e
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
cd "$(dirname "$0")/../.."
NAME=medquest-kb-chat-v2
ROLE=arn:aws:iam::$ACCOUNT_ID:role/mqd-chatbot-v2-lambda-role
# The models can be switched for a test run: ANSWER_MODEL=... UNDERSTAND_MODEL=... EFFORT=low sh lambda/v2/deploy.sh
P=arn:aws:bedrock:us-east-2:$ACCOUNT_ID:inference-profile/global.anthropic
# Default model: scored best for its cost in eval/compare.sh.
DEFAULT_MODEL=$P.claude-haiku-5-5
ENV="Variables={KNOWLEDGE_BASE_ID=HDEFCGHQPX,MODEL_ID=$DEFAULT_MODEL,UNDERSTAND_MODEL_ID=${UNDERSTAND_MODEL:-$DEFAULT_MODEL},ANSWER_MODEL_ID=${ANSWER_MODEL:-$DEFAULT_MODEL},EFFORT=${EFFORT-low},GUARDRAIL_ID=mzfny1wmoqqi,GUARDRAIL_VERSION=3,SESSIONS_TABLE=mqd-chatbot-v2-sessions,MESSAGES_TABLE=mqd-chatbot-v2-messages}"

ZIP=$(mktemp -d)/v2.zip
zip -jq "$ZIP" lambda/v2/lambda_function.py lambda/v2/estimate.py lambda/v2/crisis.py lambda/v2/bm25.py knowledge-base/build/resources.json knowledge-base/build/search-docs.json knowledge-base/build/answers.json knowledge-base/facts.json

if aws lambda get-function --function-name $NAME >/dev/null 2>&1; then
  aws lambda update-function-code --function-name $NAME --zip-file "fileb://$ZIP" --query LastModified --output text
  aws lambda wait function-updated --function-name $NAME
  aws lambda update-function-configuration --function-name $NAME --environment "$ENV" --query LastModified --output text
else
  aws lambda create-function --function-name $NAME --runtime python3.14 --handler lambda_function.lambda_handler \
    --role $ROLE --zip-file "fileb://$ZIP" --timeout 60 --memory-size 512 --environment "$ENV" \
    --description "Med-QUEST website chatbot v2 (knowledge base HDEFCGHQPX). See lambda/v2 in mqd-ai-widget." \
    --tags Project=mqd-chatbot,Owner=mqd-chatbot --query FunctionArn --output text
fi
aws lambda wait function-updated --function-name $NAME
echo deployed
