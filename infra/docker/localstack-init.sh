#!/bin/sh
set -eu
awslocal s3api create-bucket --bucket tradesentry-documents-local --create-bucket-configuration LocationConstraint=ap-south-1
awslocal s3api put-bucket-versioning --bucket tradesentry-documents-local --versioning-configuration Status=Enabled
KEY_ID=$(awslocal kms create-key --query KeyMetadata.KeyId --output text)
awslocal kms create-alias --alias-name alias/tradesentry-local --target-key-id "$KEY_ID"
awslocal dynamodb create-table \
  --table-name TradeFinanceRegistry \
  --billing-mode PAY_PER_REQUEST \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
    AttributeName=bl_number_normalized,AttributeType=S \
    AttributeName=registered_at,AttributeType=S \
    AttributeName=vessel_normalized,AttributeType=S \
    AttributeName=shipment_date_iso,AttributeType=S \
    AttributeName=exporter_normalized,AttributeType=S \
  --key-schema AttributeName=PK,KeyType=HASH AttributeName=SK,KeyType=RANGE \
  --global-secondary-indexes \
    '[{"IndexName":"gsi_bl_number","KeySchema":[{"AttributeName":"bl_number_normalized","KeyType":"HASH"},{"AttributeName":"registered_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}},{"IndexName":"gsi_vessel_date","KeySchema":[{"AttributeName":"vessel_normalized","KeyType":"HASH"},{"AttributeName":"shipment_date_iso","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}},{"IndexName":"gsi_exporter","KeySchema":[{"AttributeName":"exporter_normalized","KeyType":"HASH"},{"AttributeName":"registered_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]'
awslocal dynamodb update-time-to-live \
  --table-name TradeFinanceRegistry \
  --time-to-live-specification Enabled=true,AttributeName=ttl
