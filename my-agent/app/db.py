"""Firestore database client initialization."""

from google.cloud import firestore

# Hardcode project ID as string constant (never derive from env or auth default)
FIRESTORE_PROJECT = "qwiklabs-gcp-02-920870f66970"


def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client instance connected to FIRESTORE_PROJECT."""
    return firestore.Client(project=FIRESTORE_PROJECT)


db = get_firestore_client()
