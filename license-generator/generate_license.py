#!/usr/bin/env python3
"""
QuantDrift License Generator

Generates signed license entries and appends them to a registry file.
Only you (the vendor) run this script. The app verifies licenses using
the public key and the registry file (e.g. on Drive or a server).

Usage:
  python generate_license.py --hardware-id <HW_ID> --email user@example.com --days 365
  python generate_license.py --hardware-id <HW_ID> --email user@example.com --days 90 --registry ./drive/license_registry.json

The customer must provide their hardware_id (from the app's Settings or a helper).
Output: license key (XXXX-XXXX-XXXX-XXXX) and the registry file is updated.
"""

import argparse
import json
import os
import random
import string
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from nacl.signing import SigningKey
    from nacl.encoding import RawEncoder
except ImportError:
    print("Install dependencies: pip install pynacl")
    raise

# Registry file key
REGISTRY_LICENSES_KEY = "licenses"
DEFAULT_REGISTRY = "license_registry.json"
DEFAULT_KEY_FILE = "private_key.pem"
KEY_DIR = Path(__file__).resolve().parent


def generate_license_key() -> str:
    """Generate a key in format XXXX-XXXX-XXXX-XXXX (alphanumeric)."""
    chars = string.ascii_uppercase + string.digits
    parts = ["".join(random.choices(chars, k=4)) for _ in range(4)]
    return "-".join(parts)


def load_or_create_signing_key(key_path: Path) -> SigningKey:
    """Load existing Ed25519 private key or create and save a new one."""
    if key_path.exists():
        with open(key_path, "rb") as f:
            data = f.read()
        if len(data) != 32:
            raise SystemExit("Error: private key file must be 32 raw bytes. Delete it to regenerate.")
        return SigningKey(data)
    key = SigningKey.generate()
    with open(key_path, "wb") as f:
        f.write(bytes(key))
    # Write public key next to it for embedding in the app
    pub_path = key_path.with_suffix(".pub")
    with open(pub_path, "wb") as f:
        f.write(bytes(key.verify_key))
    print(f"Created new key pair: {key_path} and {pub_path}")
    return key


def payload_string(license_key: str, email: str, hardware_id: str, issued_at: str, expires_at: str, tier: str) -> str:
    """Canonical payload string for signing (must match Rust app)."""
    return f"{license_key}|{email}|{hardware_id}|{issued_at}|{expires_at}|{tier}"


def main():
    parser = argparse.ArgumentParser(description="Generate a signed license and add to registry")
    parser.add_argument("--hardware-id", "-H", default="", help="Customer machine hardware ID (from app)")
    parser.add_argument("--email", "-e", default="", help="Customer email")
    parser.add_argument("--days", "-d", type=int, default=None, help="Validity in days (e.g. 30, 365)")
    parser.add_argument(
        "--registry", "-r",
        default=str(KEY_DIR / DEFAULT_REGISTRY),
        help="Path to registry JSON file (created/updated). Default: ./license_registry.json",
    )
    parser.add_argument(
        "--key", "-k",
        default=str(KEY_DIR / DEFAULT_KEY_FILE),
        help="Path to Ed25519 private key (created if missing)",
    )
    parser.add_argument(
        "--license-key", "-l",
        default=None,
        help="Optional: specific license key (otherwise auto-generated)",
    )
    parser.add_argument(
        "--export-public-key",
        action="store_true",
        help="Print public key (hex) for embedding in the app and exit",
    )
    args = parser.parse_args()

    key_path = Path(args.key)
    if args.export_public_key:
        sk = load_or_create_signing_key(key_path)
        print(bytes(sk.verify_key).hex())
        return 0

    if not args.hardware_id or not args.email or args.days is None:
        parser.error("--hardware-id, --email, and --days are required (unless using --export-public-key)")
    if args.days < 1 or args.days > 3650:
        print("Error: --days must be between 1 and 3650")
        return 1

    signing_key = load_or_create_signing_key(key_path)

    license_key = args.license_key or generate_license_key()
    # Validate format
    parts = license_key.split("-")
    if len(parts) != 4 or not all(len(p) == 4 and p.isalnum() for p in parts):
        if args.license_key:
            print("Error: --license-key must be format XXXX-XXXX-XXXX-XXXX (4x4 alphanumeric)")
            return 1
        # Regenerate until valid (unlikely to need more than once)
        while len(parts) != 4 or not all(len(p) == 4 and p.isalnum() for p in parts):
            license_key = generate_license_key()
            parts = license_key.split("-")

    now = datetime.now(timezone.utc)
    issued_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    expires_at = (now + timedelta(days=args.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    tier = "pro"

    payload = payload_string(
        license_key, args.email, args.hardware_id, issued_at, expires_at, tier
    )
    signed = signing_key.sign(payload.encode("utf-8"))
    # Ed25519 signature is 64 bytes
    signature_hex = signed.signature.hex()

    entry = {
        "license_key": license_key,
        "email": args.email,
        "hardware_id": args.hardware_id,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "tier": tier,
        "signature": signature_hex,
    }

    registry_path = Path(args.registry)
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {REGISTRY_LICENSES_KEY: []}

    licenses = data.get(REGISTRY_LICENSES_KEY, [])
    # Check if entry already exists for this email + hardware_id
    existing_idx = next(
        (i for i, e in enumerate(licenses)
         if e.get("email") == args.email and e.get("hardware_id") == args.hardware_id),
        None,
    )

    if existing_idx is not None:
        old = licenses[existing_idx]
        print(f"Existing entry found for email={args.email} and hardware_id={args.hardware_id}")
        print(f"  Previous key: {old.get('license_key')} (expires: {old.get('expires_at')})")
        print(f"  Updating with new license key and expiry...")
        licenses[existing_idx] = entry
    else:
        # Avoid duplicate license_key elsewhere (same key for different email/hw = replace)
        licenses = [e for e in licenses if e.get("license_key") != license_key]
        licenses.append(entry)

    data[REGISTRY_LICENSES_KEY] = licenses

    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Registry updated: {registry_path}")
    print(f"License key:      {license_key}")
    print(f"Email:            {args.email}")
    print(f"Hardware ID:      {args.hardware_id}")
    print(f"Valid for:        {args.days} days (expires {expires_at})")
    print("\nGive the customer the license key; they enter it with their email in the app.")
    print("Upload or sync the registry file to your drive/server so the app can validate it.")
    return 0


if __name__ == "__main__":
    exit(main())
