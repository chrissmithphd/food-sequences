#!/usr/bin/env python3
"""
Download and ingest the Instacart dataset.

This script:
1. Downloads the dataset from Kaggle (if credentials are configured)
2. Extracts CSV files to data/raw/
3. Converts to Parquet format in data/processed/
4. Records provenance metadata (source, date, checksums)
"""

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    DATA_PROCESSED,
    DATA_RAW,
    KAGGLE_DATASET,
    KAGGLE_URL,
    REQUIRED_FILES,
)


def compute_checksum(file_path: Path) -> str:
    """Compute SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def download_from_kaggle(output_dir: Path) -> bool:
    """
    Download dataset from Kaggle using the API.

    Returns True if successful, False otherwise.
    """
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        print("ERROR: kaggle package not installed")
        print("Install with: uv sync")
        return False

    # Check for credentials (environment variable or token file)
    import os

    has_env_token = "KAGGLE_API_TOKEN" in os.environ
    kaggle_token_file = Path.home() / ".kaggle" / "access_token"
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"

    has_credentials = has_env_token or kaggle_token_file.exists() or kaggle_json.exists()

    if not has_credentials:
        print("ERROR: Kaggle credentials not found")
        print("\nTo set up Kaggle authentication, go to:")
        print("  https://www.kaggle.com/settings/account")
        print("\nScroll to the 'API' section and follow the instructions to generate a token.")
        print("\nThen choose ONE of these methods:")
        print("\n1. Environment variable (recommended for this session):")
        print("   export KAGGLE_API_TOKEN=KGAT_your_token_here")
        print("\n2. Save to file (persists across sessions):")
        print("   mkdir -p ~/.kaggle")
        print("   echo 'KGAT_your_token_here' > ~/.kaggle/access_token")
        print("   chmod 600 ~/.kaggle/access_token")
        print("\nNote: Kaggle changed from kaggle.json to token-based auth.")
        return False

    print("Initializing Kaggle API...")
    api = KaggleApi()

    try:
        api.authenticate()
    except Exception as e:
        print(f"ERROR: Kaggle authentication failed: {e}")
        print("\nIf you just set up your token, make sure you:")
        print("1. Exported it correctly: export KAGGLE_API_TOKEN=KGAT_...")
        print("2. OR saved it to ~/.kaggle/access_token")
        return False

    print(f"Downloading {KAGGLE_DATASET} dataset...")
    print("This may take several minutes (~200 MB download)...")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        api.dataset_download_files(KAGGLE_DATASET, path=str(output_dir), unzip=True)
        print(f"Download complete: {output_dir}")
        return True
    except Exception as e:
        print(f"ERROR: Download failed: {e}")
        print("\nPossible reasons:")
        print("1. Network error or Kaggle API issue")
        print("2. Invalid token or authentication problem")
        print("\nYou can download manually:")
        print(f"1. Visit: {KAGGLE_URL}")
        print("2. Click 'Download' button")
        print(f"3. Extract the ZIP to: {output_dir}")
        return False


def extract_zip_files(raw_dir: Path) -> bool:
    """Extract all ZIP files in the raw directory."""
    zip_files = list(raw_dir.glob("*.zip"))

    if not zip_files:
        print(f"No ZIP files found in {raw_dir} (may already be extracted)")
        return True  # Not an error - files might already be extracted

    for zip_path in zip_files:
        print(f"Extracting {zip_path.name}...")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(raw_dir)
            print(f"  Extracted {len(zf.namelist())} files")
        except Exception as e:
            print(f"ERROR: Failed to extract {zip_path}: {e}")
            return False

    return True


def find_csv_file(raw_dir: Path, possible_names: list[str]) -> Path | None:
    """Find a CSV file by searching for possible names."""
    for name in possible_names:
        # Try exact match
        path = raw_dir / name
        if path.exists():
            return path

        # Try recursive search
        matches = list(raw_dir.rglob(name))
        if matches:
            return matches[0]

    return None


def convert_to_parquet(raw_dir: Path, processed_dir: Path) -> dict[str, dict]:
    """
    Convert CSV files to Parquet format.

    Returns metadata about each file (path, checksum, row count, size).
    """
    processed_dir.mkdir(parents=True, exist_ok=True)

    file_metadata = {}

    for table_name, possible_names in REQUIRED_FILES.items():
        print(f"\nProcessing {table_name}...")

        # Find the CSV file
        csv_path = find_csv_file(raw_dir, possible_names)
        if csv_path is None:
            print(f"  WARNING: File not found. Searched for: {possible_names}")
            file_metadata[table_name] = {"status": "missing"}
            continue

        print(f"  Found: {csv_path.relative_to(raw_dir)}")

        # Read CSV
        try:
            df = pd.read_csv(csv_path)
            print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
            print(f"  Columns: {', '.join(df.columns)}")
        except Exception as e:
            print(f"  ERROR: Failed to read CSV: {e}")
            file_metadata[table_name] = {"status": "read_error", "error": str(e)}
            continue

        # Write Parquet
        parquet_path = processed_dir / f"{table_name}.parquet"
        try:
            df.to_parquet(parquet_path, index=False, engine="pyarrow")
            print(f"  Saved to: {parquet_path.name}")
        except Exception as e:
            print(f"  ERROR: Failed to write Parquet: {e}")
            file_metadata[table_name] = {"status": "write_error", "error": str(e)}
            continue

        # Compute checksums
        csv_checksum = compute_checksum(csv_path)
        parquet_checksum = compute_checksum(parquet_path)

        # Store metadata
        file_metadata[table_name] = {
            "status": "ok",
            "csv_path": str(csv_path.relative_to(raw_dir)),
            "csv_checksum": csv_checksum,
            "parquet_path": str(parquet_path.relative_to(processed_dir)),
            "parquet_checksum": parquet_checksum,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "csv_size_mb": csv_path.stat().st_size / (1024 * 1024),
            "parquet_size_mb": parquet_path.stat().st_size / (1024 * 1024),
        }

    return file_metadata


def save_provenance(processed_dir: Path, file_metadata: dict) -> None:
    """Save provenance metadata to JSON file."""
    provenance = {
        "dataset_name": "Instacart Market Basket Analysis Dataset",
        "source": KAGGLE_URL,
        "kaggle_dataset": KAGGLE_DATASET,
        "retrieval_date": datetime.now().isoformat(),
        "retrieval_method": "kaggle_api",
        "files": file_metadata,
        "notes": [
            "days_since_prior_order is capped at 30",
            "order_number is customer-relative sequence",
            "No absolute calendar dates available",
            "Test set orders have no published item labels",
        ],
    }

    metadata_path = processed_dir / "provenance.json"
    with open(metadata_path, "w") as f:
        json.dump(provenance, f, indent=2)

    print(f"\nProvenance metadata saved to: {metadata_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Download and ingest Instacart dataset"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download step (use existing files in data/raw/)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Instacart Dataset Ingestion")
    print("=" * 70)

    # Step 1: Download (unless skipped)
    if not args.skip_download:
        print("\n[1/4] Downloading dataset from Kaggle...")
        success = download_from_kaggle(DATA_RAW)
        if not success:
            print("\nDownload failed. Use --skip-download if you have the files.")
            return 1
    else:
        print("\n[1/4] Skipping download (using existing files)")

    # Step 2: Extract
    print("\n[2/4] Extracting ZIP files...")
    if not extract_zip_files(DATA_RAW):
        print("Extraction failed.")
        return 1

    # Step 3: Convert to Parquet
    print("\n[3/4] Converting CSV to Parquet...")
    file_metadata = convert_to_parquet(DATA_RAW, DATA_PROCESSED)

    # Step 4: Save provenance
    print("\n[4/4] Saving provenance metadata...")
    save_provenance(DATA_PROCESSED, file_metadata)

    # Summary
    print("\n" + "=" * 70)
    print("Ingestion Summary")
    print("=" * 70)

    ok_count = sum(1 for m in file_metadata.values() if m.get("status") == "ok")
    missing_count = sum(1 for m in file_metadata.values() if m.get("status") == "missing")
    error_count = len(file_metadata) - ok_count - missing_count

    print(f"Files processed successfully: {ok_count}/{len(file_metadata)}")
    if missing_count > 0:
        print(f"Files missing: {missing_count}")
        for name, meta in file_metadata.items():
            if meta.get("status") == "missing":
                print(f"  - {name}")
    if error_count > 0:
        print(f"Files with errors: {error_count}")
        for name, meta in file_metadata.items():
            if meta.get("status") not in ["ok", "missing"]:
                print(f"  - {name}: {meta.get('error', 'unknown error')}")

    if ok_count == len(file_metadata):
        print("\n✓ All files ingested successfully")
        print("\nNext step: Run data audit")
        print("  python scripts/audit_data.py")
        return 0
    else:
        print("\n✗ Ingestion incomplete")
        return 1


if __name__ == "__main__":
    sys.exit(main())
