# AWS resources (v2)

Definitions of the AWS resources the v2 chatbot uses, kept for reference and
for recreating them. `${ACCOUNT_ID}` stands for the AWS account number; fill it
in before using a file, for example:

    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text) envsubst < aws/kb-role-policy.json

| File | Resource |
|---|---|
| `knowledge-base.json`, `data-source.json` | Bedrock knowledge base `mqd-chatbot-kb-v2` and its S3 data source |
| `kb-role-trust.json`, `kb-role-policy.json` | IAM role `mqd-chatbot-kb-role` |
| `lambda-v2-trust.json`, `lambda-v2-policy.json` | IAM role `mqd-chatbot-v2-lambda-role` |
| `guardrail-v2.json` | Guardrail `mqd-chatbot-v2-guardrail` |

All resources are tagged `Project=mqd-chatbot`, `Owner=mqd-chatbot`.
