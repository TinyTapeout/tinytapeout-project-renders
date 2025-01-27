"""
SPDX-License-Identifier: Apache-2.0
Copyright (C) 2025 Tiny Tapeout LTD
Author: Uri Shaked

Converts all shuttle GDS files to glTF format. Optionally uploads the results to S3.

To run this script, you need to have the following environment variables set:

* AWS_ACCESS_KEY_ID - AWS access key
* AWS_SECRET_ACCESS_KEY - AWS secret key

You can also set the following environment variables:

* S3_ENDPOINT_URL - S3 endpoint URL (default: s3.amazonaws.com)
* S3_BUCKET - S3 bucket name (default: tt-shuttle-assets)

You can set these environment variables in a .env file in the same directory as this script.
"""

import argparse
import json
import logging
import os
import urllib.parse
import urllib.request
from pathlib import Path

import boto3
from dotenv import load_dotenv

from GDS2glTF.gds2gltf import gds2gltf
from render_projects import download_gds

SCRIPT_DIR = Path(__file__).parent


def main(shuttle_id: str, upload_bucket=None):
    project_list_url = f"https://index.tinytapeout.com/{shuttle_id}.json"
    req = urllib.request.Request(
        project_list_url, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req) as req:
        project_list = json.load(req)["projects"]
    logging.info(f"Found {len(project_list)} projects in shuttle {shuttle_id}")

    pdk = "sg13g2" if shuttle_id.startswith("ttihp") else "sky130A"

    for project in project_list:
        macro = project["macro"]
        gds_file = download_gds(shuttle_id, macro)

        logging.info(f"Converting {macro}")
        gltf_file = SCRIPT_DIR / "gltf" / shuttle_id / (macro + ".gds.gltf")
        gltf_file.parent.mkdir(parents=True, exist_ok=True)

        logging.info(f"Writing {gltf_file}")
        gds2gltf(gds_file, gltf_file, pdk_name=pdk)

        if upload_bucket:
            logging.info("Uploading to S3...")
            with open(gltf_file, "rb") as f:
                upload_bucket.put_object(
                    Key=f"{shuttle_id}/{macro}/{macro}.gds.gltf",
                    Body=f,
                )


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Update shuttle index")
    parser.add_argument("shuttle_id", type=str, help="Shuttle ID")
    parser.add_argument(
        "-u",
        "--upload",
        action="store_true",
        help="Upload to S3/R2",
    )
    parser.add_argument(
        "--s3-endpoint",
        type=str,
        help="S3 endpoint",
        default=os.getenv("S3_ENDPOINT_URL", "s3.amazonaws.com"),
    )
    parser.add_argument(
        "--s3-bucket",
        type=str,
        help="S3 bucket",
        default=os.getenv("S3_BUCKET", "tt-shuttle-assets"),
    )
    args = parser.parse_args()

    upload_bucket = None
    if args.upload:
        s3 = boto3.resource("s3", endpoint_url=args.s3_endpoint)
        upload_bucket = s3.Bucket(args.s3_bucket)

    main(args.shuttle_id, upload_bucket=upload_bucket)
