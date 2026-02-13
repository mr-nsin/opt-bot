# Step-by-step: Generate license, save to Google Drive, run app

## Part 1: One-time setup (vendor)

### 1.1 Create key pair and get public key for the app

```bash
cd license-generator
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

First run creates `private_key.pem` and `private_key.pub`. Export the **public key in hex** (you will use this when running the app):

```bash
python generate_license.py --export-public-key
```

**Copy the 64-character hex string** (e.g. `5a838c50f67a4abbf6c1136f1acf1e8ee630b25c62fa87cd4c16953cb552a821`). Save it somewhere safe; you will set it as `REGISTRY_LICENSE_PUBLIC_KEY_HEX` when running the app.

---

## Part 2: Generate a license and save registry to Google Drive

### 2.1 Get the customer’s machine ID

The customer opens the app, goes to the **Activate License** screen, and copies **“Your machine ID”** (or you provide a small tool that shows it). They send you that string and their **email**.

### 2.2 Generate the license (vendor)

Using the customer’s **hardware ID** and **email**, and the **validity in days** you want:

```bash
cd license-generator
source .venv/bin/activate
python generate_license.py --hardware-id "PASTE_CUSTOMER_HARDWARE_ID" --email "customer@example.com" --days 365
```

The script will:

- Append a new license entry to `license_registry.json` (in the current folder).
- Print the **license key** (e.g. `EFNA-PE5K-228J-R0O1`).

**Give the customer only the license key**; they will enter it in the app with their email.

### 2.3 Save the registry file to Google Drive

1. **Upload** `license_registry.json` to Google Drive (e.g. in a folder like “QuantDrift Licenses”).
2. **Share** the file:
   - Right‑click the file → **Share**.
   - Set to **“Anyone with the link”** → **Viewer** (so the app can read it).
   - Copy the link. It looks like:  
     `https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/view?usp=sharing`
3. **Turn it into a direct-download URL** (so the app gets raw JSON, not an HTML page):
   - From the link above, take the **file ID** (the long string between `/d/` and `/view`).
   - Direct-download URL format:  
     `https://drive.google.com/uc?export=download&id=FILE_ID`  
     Example: if the file ID is `1ABC123xyz`, the URL is  
     `https://drive.google.com/uc?export=download&id=1ABC123xyz`

**Save this URL**; you will set it as `REGISTRY_URL` when running the app.

**Whenever you add a new license** (run the generator again), **re-upload** the updated `license_registry.json` to the same Drive file (replace the file or overwrite), so the app always sees the latest list.

### 2.4 Will the customer app need permissions? What about Google Drive reliability?

**No customer permissions needed.** The registry file is shared as “Anyone with the link” (Viewer). The app does a normal HTTP GET to the URL; there is no Google login, OAuth, or app-authorization flow. The customer never sees a “permission” or “sign in to Google” prompt for the registry.

**Google Drive direct-download can be unreliable.** The URL `https://drive.google.com/uc?export=download&id=FILE_ID` sometimes returns an **HTML page** (e.g. virus-scan warning or “Confirm download”) instead of the raw JSON file. When that happens, the app gets HTML and registry parsing fails (“Registry check failed” or similar). So Drive works for some setups but is not guaranteed.

**More reliable options for production:**

- **Your own server** – Host `license_registry.json` on a domain you control (e.g. `https://yourserver.com/licenses/registry.json`). The app fetches that URL; no Drive quirks.
- **GitHub (raw)** – Put the file in a **public** repo and use the raw URL:  
  `https://raw.githubusercontent.com/YOUR_ORG/YOUR_REPO/main/license_registry.json`  
  (Anyone can read; only you push updates.)
- **Any static host** – Netlify, Vercel, S3 + CloudFront, etc., as long as the URL returns **raw JSON** (no HTML wrapper).

If you use Google Drive and see “Registry check failed” or “Parse registry” errors, switch `REGISTRY_URL` to one of the options above.

---

## Part 3: Run the app with license validation (configuration)

The app must be started with two **environment variables** set so it can fetch the registry from Google Drive and verify licenses.

### 3.1 Set the variables

- **REGISTRY_URL** – The direct-download URL of your `license_registry.json` on Google Drive (from step 2.3).  
  Example: `https://drive.google.com/uc?export=download&id=YOUR_FILE_ID`
- **REGISTRY_LICENSE_PUBLIC_KEY_HEX** – The 64-character hex public key from step 1.1.  
  Example: `5a838c50f67a4abbf6c1136f1acf1e8ee630b25c62fa87cd4c16953cb552a821`

### 3.2 How to pass them when running the app

**macOS / Linux (terminal):**

```bash
export REGISTRY_URL="https://drive.google.com/uc?export=download&id=YOUR_FILE_ID"
export REGISTRY_LICENSE_PUBLIC_KEY_HEX="YOUR_64_CHAR_HEX_PUBLIC_KEY"
npm run tauri dev
```

Or in one line:

```bash
REGISTRY_URL="https://drive.google.com/uc?export=download&id=YOUR_FILE_ID" REGISTRY_LICENSE_PUBLIC_KEY_HEX="YOUR_64_CHAR_HEX" npm run tauri dev
```

**Windows (Command Prompt):**

```cmd
set REGISTRY_URL=https://drive.google.com/uc?export=download&id=YOUR_FILE_ID
set REGISTRY_LICENSE_PUBLIC_KEY_HEX=YOUR_64_CHAR_HEX
npm run tauri dev
```

**Windows (PowerShell):**

```powershell
$env:REGISTRY_URL="https://drive.google.com/uc?export=download&id=YOUR_FILE_ID"
$env:REGISTRY_LICENSE_PUBLIC_KEY_HEX="YOUR_64_CHAR_HEX"
npm run tauri dev
```

**Optional:** Put these in a small script (e.g. `run_with_license.sh` or `run_with_license.bat`) so you don’t have to type them every time.

### 3.3 Customer flow in the app

1. Customer opens the app (you distribute it with the same env vars, or you build with the URL/key baked in or provided by your installer).
2. On the **Activate License** screen they enter:
   - **License key** (the one you gave them, e.g. `EFNA-PE5K-228J-R0O1`).
   - **Email** (same as the one you used when generating the license).
3. They click **Activate License**.
4. The app fetches the registry from Google Drive (using `REGISTRY_URL`), finds the entry for that key + email, verifies the signature with `REGISTRY_LICENSE_PUBLIC_KEY_HEX`, checks machine ID and expiry, then saves the license locally. If everything matches, the app is licensed.

---

## Quick reference

| Step | What you do |
|------|-------------|
| 1 | Run `python generate_license.py --export-public-key` → copy the 64-char hex (for app config). |
| 2 | Get customer’s hardware ID + email. Run generator with `-H`, `-e`, `-d` → get license key. |
| 3 | Upload `license_registry.json` to Google Drive, share “Anyone with link”, get link → build direct URL: `https://drive.google.com/uc?export=download&id=FILE_ID`. |
| 4 | Run app with `REGISTRY_URL=<that URL>` and `REGISTRY_LICENSE_PUBLIC_KEY_HEX=<hex>`. |
| 5 | Customer enters license key + email in app and activates. |

**Note:** If you don’t set `REGISTRY_URL` and `REGISTRY_LICENSE_PUBLIC_KEY_HEX`, the app runs in local-only mode (any key in format XXXX-XXXX-XXXX-XXXX works for 365 days; suitable only for dev/testing).
