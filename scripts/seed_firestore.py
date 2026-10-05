#!/usr/bin/env python3
"""Seed Firestore collections: claims, policies, storm_reports."""

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import db


def load_json(filepath: Path) -> list[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_collection(collection_name: str, items: list[dict], id_field: str):
    print(f"Seeding {len(items)} documents into '{collection_name}' collection...")
    batch = db.batch()
    count = 0
    for item in items:
        doc_id = str(item[id_field])
        doc_ref = db.collection(collection_name).document(doc_id)
        batch.set(doc_ref, item)
        count += 1
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
    if count % 400 != 0:
        batch.commit()
    print(f"Successfully seeded {count} documents into '{collection_name}'.")


def main():
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = root_dir / "stormdesk-kit" / "data"

    if not data_dir.exists():
        data_dir = root_dir.parent / "stormdesk-kit" / "data"

    claims_file = data_dir / "claims.json"
    policies_file = data_dir / "policies.json"
    reports_file = data_dir / "storm_reports.json"

    print(f"Loading data from {data_dir}...")
    claims = load_json(claims_file)
    policies = load_json(policies_file)
    reports = load_json(reports_file)

    seed_collection("claims", claims, "claim_id")
    seed_collection("policies", policies, "policy_id")
    seed_collection("storm_reports", reports, "id")

    print("\nFirestore seeding completed successfully!")


if __name__ == "__main__":
    main()
