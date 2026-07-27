# License Distribution Guide — LAFM Crypto Trading Terminal

## Overview

LAFM Crypto Trading Terminal uses hardware-bound licenses. Each license is tied to a unique machine fingerprint (HWID) and signed with HMAC-SHA256. The license validation happens locally; no phone-home or online activation is required.

## Client Workflow

1. **Client runs the app** on their Windows PC.
2. **App displays HWID** in the license gate screen.
3. **Client sends HWID** to LAFM via email/chat.
4. **LAFM generates license** using `scripts/generate_license.py`.
5. **Client receives `LIC-...` key** and pastes it into the app.
6. **App validates locally** and unlocks full features.

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

## License Generation (LAFM Side)

### Prerequisites

- Python 3.10+
- `backend/.env` with production `LICENSE_SECRET`
- Access to the repo

### Generate a License

```powershell
cd scripts
..\backend\venv\Scripts\python.exe generate_license.py <days_valid>
```

Example:
```powershell
..\backend\venv\Scripts\python.exe generate_license.py 365
```

Output:
```
Hardware ID: 20c578cb8507cdd747cb5287ef6418bc69fafdceb5d8edf787d0992e205edd2d
License Key: LIC-eyJod2lk-IjogIjIw-YzU3OGNi-ODUwN2Nk-ZDc0N2Ni-NTI4N2Vm-NjQxOGJj-NjlmYWZk-Y2ViNWQ4-ZWRmNzg3-ZDA5OTJl-MjA1ZWRk-MmQiLCAi-ZXhwIjog-IjIwMjYt-MDgtMjZU-MTY6NTk6-MDIuNDc0-OTA4KzAw-OjAwIiwg-InNpZyI6-ICIxZThj-YmY1Mjc1-Zjk0MTQy-ZjI4YTEy-MGU3M2Iw-ZDhmMjhj-OGU5MzY1-NGY3MmQw-MzRjY2Ni-M2VkZTIy-MTMxOGU5-In0=
Expiry: 2026-08-26T16:59:02.474908+00:00
```

The license is also saved to `scripts/license.lic`.

## Validation Logic

In `backend/license_manager.py:validate()`:

1. Decode base64 payload
2. Verify HWID matches current machine
3. Verify expiry not passed
4. Verify HMAC-SHA256 signature
5. Set `license_valid = True` if all checks pass

## Security Notes

- **Secret sharing**: `LICENSE_SECRET` must remain private. Only LAFM staff should have access.
- **No server calls**: Validation is 100% local. No license data leaves the client machine.
- **Expiration**: Licenses can have any expiry. Recommend 30/90/365 days based on tier.
- **Revocation**: There is no CRL/revocation list. If a license is compromised, a newHWID-based license should be issued.

## Packaging Before Distribution

1. Update `backend/.env` with production `LICENSE_SECRET`.
2. Rebuild backend: `npm run build:backend` (or `python -m PyInstaller trading_app.spec`).
3. Rebuild installer: `npm run build:electron`.
4. Test the installer on a clean VM or secondary PC.

## Support Flow for Clients

1. Client sends HWID.
2. LAFM runs generator script.
3. LAFM sends `LIC-...` key to client.
4. Client activates in app.
5. If activation fails, client sends screenshot + HWID + license key for debugging.
