"""Configuration constants for StormDesk application."""

import os

MEDIA_BUCKET = "stormdesk-media-8c3b70"
PROJECT_ID = "qwiklabs-gcp-02-920870f66970"
LOCATION = "us-central1"

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", LOCATION)
