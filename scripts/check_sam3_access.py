#!/usr/bin/env python3
"""Background script to check SAM 3 HuggingFace access and download when granted."""

import time
import sys
from datetime import datetime
from pathlib import Path

def check_and_download():
    """Check if SAM 3 access is granted and download if available."""
    try:
        from huggingface_hub import snapshot_download, hf_api

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking SAM 3 access...")

        # Try to get repo info - this will fail if access not granted
        api = hf_api.HfApi()
        try:
            api.repo_info("facebook/sam3")
            print("Access granted! Starting download...")

            output_dir = Path(__file__).parent.parent / "data" / "models" / "sam3"
            output_dir.mkdir(parents=True, exist_ok=True)

            snapshot_download(
                repo_id="facebook/sam3",
                local_dir=str(output_dir),
            )

            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SAM 3 downloaded to {output_dir}")
            return True

        except Exception as e:
            if "403" in str(e) or "gated" in str(e).lower():
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Access not yet granted. Will retry in 1 hour.")
                return False
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")
                return False

    except ImportError:
        print("huggingface_hub not installed")
        return False

def main():
    print("=" * 60)
    print("SAM 3 Access Checker - Running every hour")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Waiting for access to facebook/sam3 on HuggingFace...")
    print()

    while True:
        if check_and_download():
            print("\n" + "=" * 60)
            print("SUCCESS! SAM 3 has been downloaded.")
            print("=" * 60)
            sys.exit(0)

        # Wait 1 hour (3600 seconds)
        print(f"Next check at: {datetime.fromtimestamp(time.time() + 3600).strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        time.sleep(3600)

if __name__ == "__main__":
    main()
