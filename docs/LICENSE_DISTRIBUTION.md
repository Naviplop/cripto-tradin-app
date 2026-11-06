# License Distribution Guide — LAFM Crypto Trading Terminal v1.0.1

## Overview

LAFM Crypto Trading Terminal v1.0.1 uses hardware-bound licenses. Each license is tied to a unique machine fingerprint (HWID) and signed with HMAC-SHA256. The license validation happens locally; no phone-home or online activation is required.

## End-User License Workflow

### 1. Install the Application

Run the installer `Crypto Trading Terminal - LAFM Setup 1.0.1.exe` (version 1.0.1) from the `dist-electron/` directory. The NSIS installer places the application in the user-selected directory with desktop and Start Menu shortcuts.

### 2. First Launch — License Gate

On first launch the app shows the license gate screen:
- If a valid license is already stored locally, the dashboard opens automatically.
- If no license is found, the user must activate one.

### 3. Get the HWID

From the license gate screen:
- Open the backend health endpoint: `http://127.0.0.1:8765/api/health`
- Copy the value of `hwid`
- Share it with LAFM to request a license

### 4. Activate a License Key

**Option A — Paste a key:**
1. Copy the `LIC-...` license key provided by LAFM.
2. Paste it into the license field on the gate screen.
3. Click **Activate License**.

**Option B — Select a `.lic` file:**
1. Click **Choose File** and locate a `.lic` file.
2. Click **Activate License**.

### 5. Validation and Unlock

The backend validates the license entirely locally:
1. Decode the base64 payload from the key.
2. Verify the HWID in the payload matches the current machine's hardware fingerprint.
3. Verify the license has not expired.
4. Verify the HMAC-SHA256 signature using `LICENSE_SECRET` from `backend/.env`.
5. If all checks pass, full trading features are unlocked and the license status is persisted locally.

### 6. Subsequent Launches

On subsequent launches the backend checks the stored license via the health endpoint. If the license is still valid, the license gate is skipped and the dashboard loads directly.

## HWID Generation

The HWID is computed in `backend/license_manager.py:get_hardware_id()`:

```python
hwid = SHA256(
    motherboard_serial + "|" +
    cpu_processor_id + "|" +
    mac_address + "|" +
    computer_name
).hexdigest()
```

- **Windows**: uses `wmic` commands
- **macOS**: uses `ioreg` + `sysctl`
- **Linux**: reads `/sys/class/dmi/id/` and `/sys/class/net/`

## License Format

```
LIC-{base64_chunk_8}-{base64_chunk_8}-{...}
```

Decodes to JSON:
```json
{
  "hwid": "sha256-hex-string",
  "exp": "2026-08-26T16:59:02.474908+00:00",
  "sig": "hmac-sha256-hex-string"
}
```

## License Generation (Owner Side)

### Script Location
`scripts/generate_license.py`

### Usage from the Owner Machine

```powershell
cd scripts
python generate_license.py 365
python generate_license.py --hwid <HWID_DEL_AMIGO> 365
python generate_license.py --hwid <HWID_DEL_AMIGO> 30 --note "trial"
```

Each generated license is appended to the owner-local registry:
`backend/licenses_registry.json`

### License Registry Format

```json
{
  "licenses": [
    {
      "key": "LIC-...",
      "hwid": "20c578cb8507cdd747cb5287ef6418bc69fafdceb5d8edf787d0992e205edd2d",
      "days_valid": 365,
      "note": "",
      "issued_at": "2026-07-29T10:00:00+00:00"
    }
  ],
  "revoked": []
}
```

## Admin API (Owner Remote Control)

Set `ADMIN_API_KEY` in `backend/.env` before distribution.

### Endpoints

- `GET /api/admin/licenses` — list issued/revoked licenses
- `POST /api/admin/issue` — issue a license remotely
  ```json
  {"target_hwid":"<hwid>","days_valid":365,"note":"client name"}
  ```
- `POST /api/admin/revoke` — revoke a license remotely
  ```json
  {"target_hwid":"<hwid>","reason":"chargeback"}
  ```
- `DELETE /api/admin/licenses` — clear registry

All admin endpoints require either:
- Header `X-Admin-Token: <ADMIN_API_KEY>`
- Query param `?admin_token=<ADMIN_API_KEY>`

## Packaging Before Distribution

1. Update `backend/.env` with production `LICENSE_SECRET`.
2. Rebuild backend: `python -m PyInstaller trading_app.spec`.
3. Build Electron app: `.\scripts\deploy.ps1 -Version 1.0.1 -Publish` or `npm run build:electron`.
4. Distribute `dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.1.exe`.

## Support Flow for Clients

1. Client sends HWID.
2. Owner runs `python generate_license.py --hwid <hwid> 365`.
3. Owner sends `LIC-...` key to client.
4. Client activates in app.
5. If activation fails, client sends screenshot + HWID + license key for debugging.

## Owner Maintenance Commands

```powershell
# list all issued licenses
curl -H "X-Admin-Token: <ADMIN_API_KEY>" http://127.0.0.1:8765/api/admin/licenses

# revoke a license
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: <ADMIN_API_KEY>" http://127.0.0.1:8765/api/admin/revoke -d "{\"target_hwid\":\"<hwid>\",\"reason\":\"...\"}"
```
