#!/bin/sh
# Creates the public endpoint for the v2 Lambda: REST API, POST /chat, API key
# required, usage plan with rate and daily limits, and a concurrency cap on the
# Lambda. Run once; prints the URL, never the key (the key goes to .env).
#
#   sh aws/create-api.sh
set -e
REGION=us-east-2
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FN=medquest-kb-chat-v2
FN_ARN=arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FN
TAGS="Project=mqd-chatbot,Owner=mqd-chatbot"

API=$(aws apigateway create-rest-api --name mqd-chatbot-v2-api --description "Public endpoint for the Med-QUEST website chatbot v2" \
  --endpoint-configuration types=REGIONAL --tags "$TAGS" --query id --output text)
ROOT=$(aws apigateway get-resources --rest-api-id "$API" --query 'items[?path==`/`].id' --output text)
RES=$(aws apigateway create-resource --rest-api-id "$API" --parent-id "$ROOT" --path-part chat --query id --output text)
aws apigateway put-method --rest-api-id "$API" --resource-id "$RES" --http-method POST --authorization-type NONE --api-key-required >/dev/null
aws apigateway put-integration --rest-api-id "$API" --resource-id "$RES" --http-method POST --type AWS_PROXY \
  --integration-http-method POST --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$FN_ARN/invocations" >/dev/null
aws lambda add-permission --function-name "$FN" --statement-id mqd-chatbot-v2-api --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API/*/POST/chat" >/dev/null
aws apigateway create-deployment --rest-api-id "$API" --stage-name prod >/dev/null

# Limits: 10 requests a second (bursts of 20), 20,000 a day.
PLAN=$(aws apigateway create-usage-plan --name mqd-chatbot-v2-plan --api-stages "apiId=$API,stage=prod" \
  --throttle burstLimit=20,rateLimit=10 --quota limit=20000,period=DAY --tags "$TAGS" --query id --output text)
KEY=$(aws apigateway create-api-key --name mqd-chatbot-v2-widget-server --enabled --tags "$TAGS" --query id --output text)
aws apigateway create-usage-plan-key --usage-plan-id "$PLAN" --key-id "$KEY" --key-type API_KEY >/dev/null

# At most 10 bot runs at once, whatever reaches the Lambda.
aws lambda put-function-concurrency --function-name "$FN" --reserved-concurrent-executions 10 >/dev/null

URL="https://$API.execute-api.$REGION.amazonaws.com/prod/chat"
VALUE=$(aws apigateway get-api-key --api-key "$KEY" --include-value --query value --output text)
# .env: the widget server sends CHAT_API_KEY with every request. The live bot's address is kept as CHAT_API_URL_V1.
python3 - "$URL" "$VALUE" <<'PY'
import sys, re
url, key = sys.argv[1], sys.argv[2]
s = open(".env").read()
old = re.search(r"^CHAT_API_URL=(.*)$", s, re.M)
if old and "CHAT_API_URL_V1=" not in s:
    s = s.replace(old.group(0), f"CHAT_API_URL_V1={old.group(1)}\nCHAT_API_URL={url}")
else:
    s = re.sub(r"^CHAT_API_URL=.*$", f"CHAT_API_URL={url}", s, flags=re.M)
s = re.sub(r"^CHAT_API_KEY=.*\n?", "", s, flags=re.M).rstrip("\n") + f"\nCHAT_API_KEY={key}\n"
open(".env", "w").write(s)
PY
echo "API id: $API"
echo "URL:    $URL"
echo "Key:    saved to .env as CHAT_API_KEY"
