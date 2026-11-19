#!/bin/sh
# Compares model setups on both test sets, graded, each question twice.
# Redeploys the Lambda per setup and restores the default at the end.
#
#   sh eval/compare.sh
set -e
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
cd "$(dirname "$0")/.."
P=arn:aws:bedrock:us-east-2:$ACCOUNT_ID:inference-profile/global.anthropic
OUT=eval/results/compare-$(date +%Y-%m-%d-%H-%M); mkdir -p "$OUT"
run() {  # name understand-model answer-model effort
  UNDERSTAND_MODEL=$P.$2 ANSWER_MODEL=$P.$3 EFFORT=$4 sh lambda/v2/deploy.sh >/dev/null
  start=$(date +%s)
  node eval/run.mjs --lambda medquest-kb-chat-v2 --grade --repeat 2 --parallel 6 --label "$1" > "$OUT/$1-main.log" 2>&1
  node eval/run.mjs --lambda medquest-kb-chat-v2 --grade --repeat 2 --parallel 6 --label "$1" --set eval/holdout.json > "$OUT/$1-holdout.log" 2>&1
  echo "$1 $start $(date +%s)" >> "$OUT/windows.txt"
}
run haiku-4-5  claude-haiku-4-5-20251001-v1:0 claude-haiku-4-5-20251001-v1:0 ""
run haiku-5-5  claude-haiku-5-5               claude-haiku-5-5               low
run sonnet-5-5 claude-haiku-5-5               claude-sonnet-5-5              low
sh lambda/v2/deploy.sh >/dev/null
echo "done: $OUT"
