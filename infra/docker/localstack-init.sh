#!/bin/sh
set -eu
awslocal s3api create-bucket --bucket tradesentry-documents-local --create-bucket-configuration LocationConstraint=ap-south-1
awslocal s3api put-bucket-versioning --bucket tradesentry-documents-local --versioning-configuration Status=Enabled
KEY_ID=$(awslocal kms create-key --query KeyMetadata.KeyId --output text)
awslocal kms create-alias --alias-name alias/tradesentry-local --target-key-id "$KEY_ID"
