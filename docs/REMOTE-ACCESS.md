# Remote access from Android and other computers (Windows 11 host)

This update prepares the existing app for Cloudflare Tunnel + Cloudflare Access. It does **not** publish your PC automatically, buy a domain, create an account, or change your router. Keep the same database/photo/model folder. No database migration or model retraining is required for this update.

## What your team will use

Each approved user opens an HTTPS address such as `https://photos.yourdomain.com`, signs in using a code emailed by Cloudflare Access, and uses the existing app. Everyone allowed into the app has the same permissions, including deletion and settings. The host PC must be awake with Internet access and both the app and tunnel running. Photos/models remain on your PC; requests and photo transfers pass through Cloudflare. No VPN installation is required on phones.

## 1. Update the app first

Stop the app and any training process. Back up the existing data folder. Copy the updated source into your existing installation, preserving `data`, `.venv`, and your existing models. Run the setup/build steps in [WINDOWS.md](WINDOWS.md). There is a new JWT verification dependency, so install the updated Python requirements as well as building the frontend.

Confirm the updated app works locally before setting up remote access. New training uploads and explicit Add to Training Library actions start approved; existing approvals are not changed. The checkbox remains editable. A shot type is still required for dataset export. Paste, trash/restore, and changes to the normal shot type retain their existing approval-reset behavior.

## 2. Choose a domain and set up Cloudflare

A domain is a name you register and renew, such as `yourbusiness.com`. You can use a subdomain such as `photos.yourbusiness.com` for this app. Check both the initial and renewal price before buying. You do not need website hosting from the registrar.

Create your own Cloudflare account and add the domain. If the domain was purchased elsewhere, follow Cloudflare's instructions to set its nameservers at the registrar. Wait until Cloudflare shows the domain as active. Do not share your password, tunnel token, recovery codes, or API keys in chat or GitHub.

Open Cloudflare Zero Trust / Cloudflare One and choose the Free plan. Record your **team domain**, in the form `yourteam.cloudflareaccess.com`. Enable **One-time PIN** as a login method. Dashboard labels can change; the current official guides are linked below.

## 3. Protect the app address BEFORE publishing a tunnel route

In Cloudflare Access, create a **Self-hosted** application:

- Application domain: your chosen address, for example `photos.yourbusiness.com`.
- Protect the **entire hostname**, including `/api`, images, and all paths. Leave the path restriction empty.
- Add an **Allow** policy that includes the exact email addresses of your 3–4 users.
- Use the One-time PIN login method. Do not use Everyone or a Bypass policy.
- Choose a reasonable login duration for a work session, for example 8 hours.
- Copy the application's **Audience (AUD) tag** from its settings.

The team domain and AUD identify the Access application. They are configuration values, not passwords. The app independently verifies the token's signature, issuer, audience, expiry, and user identity; it does not trust an email header alone.

## 4. Configure the existing Windows app

In your existing project folder, copy `remote-config.example.json` to `remote-config.json`. Open the copy in Notepad and fill it in:

```json
{
  "public_url": "https://photos.yourbusiness.com",
  "team_domain": "yourteam.cloudflareaccess.com",
  "audience": "YOUR-ACCESS-APPLICATION-AUD-TAG",
  "data_dir": "C:/Projects/vehicle-photo-qc/data"
}
```

Use **your actual existing data folder**, containing `qc.db`. The example location is not automatically correct for your computer. Use forward slashes in JSON paths, as shown. The remote startup script refuses a data folder without an existing database. Your filled-in file is excluded from Git.

Stop the local app with Ctrl+C. Open PowerShell in the project folder and run:

```powershell
.\scripts\start-remote-windows.ps1
```

If Windows blocks PowerShell scripts, you can instead run these commands one by one, using your own values:

```powershell
$env:QC_PUBLIC_URL = "https://photos.yourbusiness.com"
$env:QC_ACCESS_TEAM_DOMAIN = "yourteam.cloudflareaccess.com"
$env:QC_ACCESS_AUD = "YOUR-ACCESS-APPLICATION-AUD-TAG"
$env:QC_DATA_DIR = "C:\Projects\vehicle-photo-qc\data"
.\.venv\Scripts\python.exe -m uvicorn qc.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers
```

The app stays bound to `127.0.0.1`. Do not change it to `0.0.0.0` or open port 8000 on your router. In protected mode, **everyone, including you on the host PC, uses the HTTPS address and signs in**. Opening localhost directly will return a sign-in-required response. This prevents a local-address bypass of remote authentication.

Incomplete remote settings stop startup. Missing or invalid login tokens are denied rather than falling back to anonymous access.

## 5. Install and connect Cloudflare Tunnel

In Cloudflare's tunnel dashboard, create a remotely managed **Cloudflared** tunnel. Choose Windows and follow the install/run command shown for your own tunnel. If it asks for an administrator terminal to install the Windows service, use that only for this installation step. Treat the displayed tunnel token as a password.

Add a published application route:

- Public hostname: the **exact same** hostname protected in step 3.
- Service type: **HTTP**.
- Service URL: **127.0.0.1:8000**.
- Keep the original HTTP Host header; do **not** override it to localhost.

Do not add a second unprotected hostname, bypass route, or Quick Tunnel for this app. Configure a Cloudflare cache rule to **bypass caching for the entire app hostname**, especially photos and API responses. The app also sends `Cache-Control: no-store` in remote mode.

The tunnel makes an outbound connection from your PC; router port forwarding is not needed. Its Windows service can run in the background, while the app runs in the PowerShell window. Keep that window open.

## 6. Test before inviting the rest of the team

1. On your PC, open the HTTPS address. Confirm you must sign in and your existing library appears.
2. Open an incognito window and try an email not in the Allow policy. Confirm it cannot reach the app.
3. On Android, turn Wi-Fi off temporarily and open the address in Chrome using cellular data. Sign in with an allowed email.
4. Upload a small test vehicle, use Take photo, inspect the results, save a training label, and change a test dealership setting.
5. Confirm all devices see the same vehicle and labels.
6. Try a representative full photo batch. If a transfer fails, keep the page open and submit again: the same staged upload is retried without making another vehicle.
7. Check the app still works after stopping/restarting it with the remote startup script.

Android's camera chooser varies by phone. **Take photo** requests the rear camera where supported; the ordinary photo picker is still available. Use JPEG/PNG/WebP. Configure the camera for JPEG if it produces HEIF/HEIC. Actual camera behavior must be checked on your phones; browser automation cannot confirm the native Android camera app.

## Uploads and availability

The browser sends one photo per request (up to 25 MB per photo), then submits the vehicle once all photos are ready. This fits beneath Cloudflare's Free-plan 100 MB per-request limit. The existing 200-photo / 1 GB vehicle limits remain. Originals keep their bytes; the app does not shrink them to fit the tunnel.

Completed vehicle imports are transactional. A partial upload does not appear in the library or training data. Progress is retained on the server across app restarts; retry from the same open page to reuse it. Reloading/closing that page loses the browser's retry reference. Abandoned staging files expire after 24 hours and are cleaned on startup or when the next upload starts. At most eight unfinished batches can be staged at once. These are temporary files under `upload-staging`, separate from your existing library. If you reach the limit due to abandoned browser tabs, allow them to expire; do not delete the main data folder.

In Windows 11 **Settings → System → Power**, set the PC not to sleep while plugged in. The screen can turn off. A reboot, power outage, or lost home Internet connection makes the app unavailable until it is running again. For this prototype, start the remote app after signing into Windows. Fully unattended app startup and cloud migration can be added later.

Back up the full existing data folder regularly with the app and training stopped. The provided backup script includes committed photos, labels, database, datasets, and models; unfinished uploads are not library backups. Home upload speed affects how quickly remote users can view photos.

## Returning to local-only mode

Stop the tunnel service first, then stop the app. In a fresh PowerShell window without remote environment variables, run the normal `scripts\start-windows.ps1`. If you set the variables persistently in Windows, remove `QC_PUBLIC_URL`, `QC_ACCESS_TEAM_DOMAIN`, and `QC_ACCESS_AUD` before local-only startup. Keep `QC_DATA_DIR` pointing to the same library. Local mode refuses requests bearing Cloudflare tunnel headers to help prevent accidental anonymous publication.

## Troubleshooting

- **401 / sign in through the configured address:** use the HTTPS URL, verify the team domain and Access AUD, and confirm Access protects all paths. Do not disable authentication to fix it.
- **403 when saving/uploading:** `public_url` must exactly match the address in the browser, including HTTPS. Do not include a trailing path or use an alternate hostname.
- **Cloudflare 502:** confirm the PC/app are running and the tunnel service URL is `http://127.0.0.1:8000`.
- **Login expired during upload:** sign in again using a second tab, then retry from the original upload tab.
- **Empty library:** stop the app and correct the data-folder path before importing anything.
- **Cannot save a selected training example:** give it a shot type other than Unknown, or uncheck approval until ready.

## Official reference guides

- [Cloudflare Zero Trust pricing](https://www.cloudflare.com/plans/zero-trust-services/)
- [Email PIN login](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/)
- [Protect a self-hosted application](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/)
- [Create a tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/)
- [Validate Access tokens](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)
- [Cloudflare request-size limits](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/)
