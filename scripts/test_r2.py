"""Weryfikacja połączenia z Cloudflare R2."""

import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

required = ["R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT", "R2_BUCKET"]
missing = [k for k in required if not os.environ.get(k)]
if missing:
    print(f"[FAIL] Brak zmiennych w .env: {missing}")
    sys.exit(1)

endpoint = os.environ["R2_ENDPOINT"]
bucket = os.environ["R2_BUCKET"]
public_url = os.environ.get("R2_PUBLIC_URL", "(nieustawiony)")

print(f"Endpoint : {endpoint}")
print(f"Bucket   : {bucket}")
print(f"Public URL: {public_url}")

try:
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    resp = s3.list_objects_v2(Bucket=bucket, MaxKeys=5)
    count = resp.get("KeyCount", 0)
    print(f"[OK] Połączenie z R2 działa. Obiektów w bucket: {count}")
    if count > 0:
        keys = [o["Key"] for o in resp.get("Contents", [])]
        print(f"     Przykłady: {keys}")
    sys.exit(0)
except NoCredentialsError:
    print("[FAIL] Brak lub błędne credentials (NoCredentialsError)")
    sys.exit(1)
except ClientError as exc:
    code = exc.response["Error"]["Code"]
    msg = exc.response["Error"]["Message"]
    print(f"[FAIL] ClientError {code}: {msg}")
    sys.exit(1)
except Exception as exc:
    print(f"[FAIL] {type(exc).__name__}: {exc}")
    sys.exit(1)
