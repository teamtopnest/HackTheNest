# Base44 Project

Use this repository to run and edit the app locally, then publish changes back through Base44.

Any change pushed to the repo will also be reflected in the Base44 Builder.

## Standalone Frontend Preview

The current landing page is configured as a frontend-only Vite app. Its inquiry form is a visual demo and does not transmit or store information. Do not enter real personal information until a production submission service is connected.

From the `app` directory:

```bash
npm install
npm run dev
```

Open the local URL printed by Vite (typically `http://localhost:5173`). Create a production build with:

```bash
npm run build
npm run preview
```

The **Start acquisition** link opens `/acquisition`. On the headset computer,
start the Python service separately using `backend\scripts\stream.ps1` from
the repository root, and configure MongoDB in `backend\.env`. The page uses
`http://127.0.0.1:8000` by default; `VITE_EEG_API_URL` can override the address
at build time. The backend currently accepts browser origins on port 5173 only.

Choose a model, scan, select a serial and check it. Continue to the calibration
and synchronization guidance page before opening a preview. The check opens and
releases the device; the uncalibrated live preview reopens it and writes filtered
EEG to MongoDB. Closing a WebSocket-started page ends that collection. Core and
g.Nautilus hardware adapters remain experimental; g.Nautilus requires a working
g.tec Device Service/base station and the selected variant is not verified by
the driver. Electrode positions are not inferred from channel indices.

The calibration page is an operator checklist with three steps. The workspace
button stays disabled until all three are completed:

1. **Alignment** — review the 10–20 reference image (Fz, Cz, P3, Pz, P4, PO7,
   PO8, Oz), then select **Mark alignment as good**.
2. **Calibration** — **Run Calibration**, then **Calibration completed**.
3. **Synchronization** — **Run Synchronization**, then
   **Synchronization completed**.

No measurement API is connected. With a headset, **Run** starts the manual
procedure for the operator to perform with the manufacturer's tools. In demo
mode it plays a short simulated run. **Completed** records an operator
confirmation only. It does not verify fitting, impedance, signal quality,
channel mapping or stimulus timing, and the live preview stays uncalibrated for
P300 purposes. Checklist state resets when the page is reopened or the headset
or mode changes. The contact and synchronization figures are illustrations, not
live values.

For a headset-free preview, enable **Demo mode** and open the calibration page.
Complete the three steps and select **Open demo workspace**, or use
**Skip checks (demo only)**. The skip link is not shown for a live headset.
The browser generates synthetic traces locally; no headset or MongoDB is used
and no demo EEG data is saved. Demo speech uses the local backend and
ElevenLabs as described below. The g.Nautilus demo channel count is only an
illustrative preset, not a device measurement.

### ElevenLabs demo speech

On the computer running the local EEG service, create the ignored
`backend\.env.local` file and add these values (do not put the key in frontend
code or chat):

```text
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_VOICE_ID=your_voice_id
```

Get the API key from ElevenLabs and choose a voice ID from your ElevenLabs
account. Environment variables take precedence, followed by `.env.local` and
then the existing `.env`. Restart the backend with `.\backend\scripts\stream.ps1` from the
repository root. Demo speech is enabled by default; start flashing in the
demo workspace. Each synthetic result is spoken once, including intermediate
choices (for example, "I want food", "I want fast food", "I want pizza").
Use **Disable demo speech** to turn it off.
If the browser blocks automatic playback, use the **Play speech** button.
Errors, including missing configuration or provider failures, are shown in
the workspace. An ElevenLabs HTTP 402 response requires checking the account's
credits and billing.

Only predefined demo menu paths are accepted by the speech endpoint; the
corresponding synthetic phrase is sent to ElevenLabs. Do not use the demo
for real patient choices or enter patient information. Live acquisition does
not trigger speech. The local backend is unauthenticated and is not suitable
for public exposure.

### Vultr frontend and cloud API

The cloud service is `backend.app:app`, not the Bluetooth service
`eeg_stream.app:app`. Install `backend/requirements-cloud.txt` on Ubuntu; it
does not install the Windows headset drivers or g.Pype. The cloud service
supports authenticated ingestion, `/health`, and authenticated synthetic demo
speech. Live headset acquisition still runs locally and is not yet bridged
to cloud ingestion.

Copy `backend/deploy/backend.env.example` to
`/etc/hackthenest/backend.env` on the server and replace placeholders privately.
Use rotated credentials. Generate two different random tokens of at least
32 characters: `EEG_API_TOKEN` for ingestion and `EEG_DEMO_TOKEN` for browser
demo speech. Never put either token, the database URI, or ElevenLabs key in a
`VITE_` variable. `EEG_ALLOWED_ORIGINS` is a comma-separated list of exact
frontend origins. The service requires MongoDB connectivity at startup.

Build the frontend with `VITE_EEG_SPEECH_API_URL=https://api.neuronvision.us`.
Keep `VITE_EEG_API_URL` pointing to loopback for local acquisition; do not
point headset discovery requests to Vultr. Enter `EEG_DEMO_TOKEN` in the
workspace's **Cloud demo speech access token** field. It remains in React
memory only and must be re-entered after a reload; it cannot access ingestion.

Deploy the backend package, the shared
`app/src/lib/communication-menu.json`, and `app/dist` to
`/opt/hackthenest/app`. Do not upload `.env` files, virtual environments, caches
or the repository's full Git directory. Create a Python virtual environment
at `/opt/hackthenest/venv`, then install the cloud requirements. Install
`backend/deploy/neuronvision.service` as the systemd unit and
`backend/deploy/neuronvision.nginx` as an enabled Nginx site. These expect an
unprivileged `hackthenest` account and a root-owned environment file readable
by its group. The API listens only on `127.0.0.1:8000`.

Point root and `api` A records to Vultr and `www` CNAME to the root domain.
After installing the Nginx site, obtain certificates with Certbot's Nginx
plugin for all three names and enable HTTP-to-HTTPS redirects. The API proxy
rejects plaintext requests until HTTPS is available. The speech endpoint is
limited to 10 requests/minute per IP with a burst of 3 at Nginx.

Validate the service with `https://api.neuronvision.us/health`, confirm
unauthenticated speech requests return 401, and test the hosted demo.
Browser autoplay policy may still require **Play speech**. Hosted real
headset acquisition additionally needs an authenticated local bridge and
browser local-network permissions; the cloud deployment alone does not
enable it.

In the demo workspace, **Start flashing** opts into visual flashing (a one-line
reminder to stop if uncomfortable stays next to the button). The demo randomly
chooses an attended item and adds synthetic event-related responses to noisy
traces. After each flash of the attended item, a P300-like positive wave
(~300 ms, ±30 ms trial jitter, parietal-weighted over the reference montage
Fz, Cz, P3, Pz, P4, PO7, PO8, Oz) appears on all 8 channels. The signal panel marks every
flash with a dashed line, and attended flashes with a green line and shaded
250–500 ms window. On desktop, the demo uses a 20% / 50% / 30% layout:
electrode traces on the left, the communication menu in the center, and
**Averaged responses by item** on the right. Up to eight electrodes fit the
left sidebar without internal scrolling; larger counts enable a dark/blue
scrollbar. The right sidebar fits all item graphs in two columns, resizing them
to the available height. Both panels stay visible while scrolling. On unusually
short desktop windows, panels keep a 620px minimum height so the page scrolls
instead of clipping the charts. Panels stack on smaller screens.
The live preview keeps the left electrode sidebar but has no synthetic ERP
sidebar. Menu buttons contain only labels and evidence bars.
The separate response sidebar shows one graph per item, with
distinct colored electrode averages overlaid (0–700 ms, shared -20 to 40 µV
scale) and a matching legend. Each electrode is baseline-corrected separately
and averaged over repeated flashes, preserving its own waveform and amplitude.
As flashes accumulate, the attended item's curves form clear peaks while the
others average towards flat. The menu has three choice levels (category,
subcategory, final option), including Food, Drink, Move, Pain, Help, Family and
Friends. Every menu includes Other. Navigation follows the selected node, so
repeated labels such as Home or Other do not link to unrelated menus.
Intermediate menus use four balanced flashing rounds. Final-level menus use
five rounds and require five positive demo scores plus a margin over the
runner-up. These thresholds are illustrative, not calibrated probabilities or
measured accuracy.

The "You've chosen …" modal has no action buttons. Intermediate choices remain
visible for five seconds, then automatically open the chosen submenu, clear
ERP averages/evidence/markers and begin flashing its items. Final choices stop
flashing and remain visible for 25 seconds, then return to the main menu with
options and signals reset. Collection continues; flashing remains stopped until
Start flashing is selected again. An inconclusive result displays for five
seconds before retrying the same menu. Navigation or stopping collection
cancels pending transitions.

Real P300 decoding, synchronized stimulus markers and patient-specific
thresholds are not implemented; the live workspace menu is manual and keeps its
"decoding not active" notice. The current service is a local,
unauthenticated prototype: a hosted HTTPS frontend and a remotely deployed
backend require a secure local acquisition bridge, authentication, browser
origin and TLS configuration before production use.

## Host on Vercel

1. Import the Git repository into Vercel and set the project **Root Directory** to `app`.
2. Select the Vite framework preset, use `npm install` as the install command, `npm run build` as the build command, and `dist` as the output directory.
3. Deploy the site and add your domain in the Vercel project’s **Settings → Domains**.
4. At the DNS provider authoritative for the domain (GoDaddy or Porkbun, whichever currently hosts its DNS), add the records Vercel displays. Do not change nameservers or existing records unless Vercel specifically instructs you to; DNS changes can interrupt other services using the domain.
5. Wait for Vercel to verify DNS and issue HTTPS, then test the domain on desktop and mobile.

This static hosting setup does not deploy the Python backend or connect the inquiry form to Base44. Keep the existing Base44 publishing instructions below only if you later choose to use that platform.

## Prerequisites

1. Clone the repository using the project's Git URL.
2. Navigate to the project directory.
3. Install dependencies: `npm install`.
4. Install the Base44 CLI: `npm install -g base44@latest`.
5. Install [Deno](https://docs.deno.com/runtime/getting_started/installation/) — the local Base44 backend runs on it.

Run `base44 --help` (or see the [CLI reference](https://docs.base44.com/developers/references/cli/commands/introduction)) for the full command surface.

## Run Locally

Three commands, from the project root:

```bash
base44 login   # one-time per machine
base44 link    # one-time per clone
base44 dev     # local backend + frontend together
```

Open the frontend URL that `base44 dev` prints (typically `http://localhost:5173`).

Notes:

- **Every fresh clone needs `base44 link`.** It writes `base44/.app.jsonc` (the app-id pointer), which is deliberately gitignored. Your app id is in the Builder URL (`app.base44.com/apps/<id>/...`); `base44 link --help` shows the non-interactive flags.
- **`base44 dev` runs the frontend for you** (via `site.serveCommand` in this repo's `base44/config.jsonc`) — never run `npm run dev` yourself: alone it serves a UI with no backend behind it (`[base44] Proxy not enabled`, every `/api` call fails), and alongside `base44 dev` the second Vite silently takes the next port and you end up looking at the wrong one.
- **The app must be published at least once for the UI to load under `base44 dev`.** The frontend boots by fetching app settings from the hosted app; before the first publish that fails and every page redirects to login. The local API works regardless.
- Entities, functions, and auth run locally — entity data is **in-memory only**, wiped when `base44 dev` restarts. Everything else (Core integrations, OAuth login) is forwarded to your deployed app. Full breakdown: [Local development overview](https://docs.base44.com/developers/backend/overview/local-dev/local-development-overview).

## Frontend Only, Hosted Backend

To work on just the frontend against your app's live hosted backend:

```bash
base44 dev --remote
```

⚠️ In this mode writes go to your app's **production data** — plain `base44 dev` keeps everything local.

## Publish Your Changes

After pushing your changes to git, open the Base44 dashboard and publish the app:

```bash
base44 dashboard open
```

This repo syncs to Base44 through git, so publish from the dashboard rather than `base44 deploy` — a CLI deploy ships your local tree directly, bypassing the sync, and the deployed state silently diverges from the repo.

## Docs & Support

GitHub integration: [https://docs.base44.com/developers/app-code/local-development/github](https://docs.base44.com/developers/app-code/local-development/github)

Local development: [https://docs.base44.com/developers/backend/overview/local-dev/local-development-overview](https://docs.base44.com/developers/backend/overview/local-dev/local-development-overview)

Support: [https://app.base44.com/support](https://app.base44.com/support)
