# QuantDrift License Generator

Run this only on your machine (the vendor). It generates signed licenses and appends them to a **registry file**. The app validates licenses against this registry (e.g. from a shared drive or server).

**→ Full step-by-step (generate license → save to Google Drive → run app):** see [../docs/LICENSE_SETUP_STEPS.md](../docs/LICENSE_SETUP_STEPS.md).

## Setup

```bash
cd license-generator
pip install -r requirements.txt
```

## First run: create key pair

The first time you run the script it will create:

- `private_key.pem` – 32-byte Ed25519 private key (keep secret, never ship).
- `private_key.pub` – 32-byte public key. You must embed this in the app (see below).

## Embed public key in the app

After creating the key pair, get the public key in hex:

```bash
python generate_license.py --export-public-key
```

Copy the hex string and set it in the app (see `docs/LICENSE_SYSTEM.md` or the app’s registry config). The app uses this to verify that registry entries were signed by you.

## Generate a license

The customer must send you their **hardware ID** (from the app’s license/Settings screen or a helper you provide) and their **email**.

```bash
python generate_license.py --hardware-id <CUSTOMER_HARDWARE_ID> --email customer@example.com --days 365
```

Options:

- `--hardware-id` / `-H` – Customer’s machine hardware ID (required).
- `--email` / `-e` – Customer email (required).
- `--days` / `-d` – Validity in days (required, 1–3650).
- `--registry` / `-r` – Path to the registry JSON file (default: `./license_registry.json`).
- `--key` / `-k` – Path to your private key file (default: `./private_key.pem`).
- `--license-key` / `-l` – Optional: specific key (e.g. `ABCD-1234-EFGH-5678`); otherwise one is generated.

The script will:

1. Create a license entry (key, email, hardware_id, issued_at, expires_at, tier, signature).
2. Append it to the registry file (creating the file if needed).
3. Print the **license key** to give to the customer.

Example:

```bash
python generate_license.py -H a1b2c3d4... -e user@example.com -d 365 -r ./drive/license_registry.json
```

## Registry file and “drive”

- The **registry** is a single JSON file (e.g. `license_registry.json`) with a `licenses` array. Each new license is **appended** to that array.
- **Store it on “drive”**: upload or sync this file to Google Drive, OneDrive, or your server so the app can load it (via a URL or path you configure in the app). If you add a new license with the script, re-upload/sync the updated file so the app sees it.
- **Revocation**: remove the corresponding entry from the registry and re-upload; the app will treat the license as invalid on the next check.

## Security summary

- Only the **generator** (this script) has the **private key**; the app only has the **public key** and cannot create valid licenses.
- Validity (days) and hardware ID are **embedded** in the signed payload; the app verifies the signature and checks hardware and expiry.
- The app checks the registry **periodically** so revocations and expiry are enforced.
