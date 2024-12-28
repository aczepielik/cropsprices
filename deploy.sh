#!/bin/bash

# Check if environment argument is provided
if [ -z "$1" ]; then
    echo "Usage: ./deploy.sh [staging|prod]"
    exit 1
fi

ENV=$1

if [ "$ENV" != "staging" ] && [ "$ENV" != "prod" ]; then
    echo "Environment must be either 'staging' or 'prod'"
    exit 1
fi

echo "Deploying to $ENV environment..."

# Submit the build
gcloud builds submit --config="cloudbuild.$ENV.yaml"

# Wait for deployment to complete
gcloud run services describe "crops-prices-app-$ENV" \
    --region us-central1 \
    --format='value(status.url)'