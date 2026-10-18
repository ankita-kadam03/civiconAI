# Firebase Hosting (frontend)

**Primary URL:** https://civiconai.web.app (Firebase site id `civiconai`)  
**Legacy default URL:** https://inlaid-reactor-402513.web.app (still works if you deploy to both sites)  
**Custom domain (optional):** https://civiconai.com — connect in Firebase Console → Hosting  
**API:** https://civicon-api-738610733968.asia-south1.run.app

Firebase Hosting always uses **HTTPS** (`https://civiconai.com`), not `http://`.

---

## Deploy frontend

```bash
npm run deploy:web
```

Requires `frontend/.env.production` with `VITE_API_BASE_URL` pointing at Cloud Run.

---

## Custom domain: civiconai.com

1. [Firebase Console](https://console.firebase.google.com/project/inlaid-reactor-402513/hosting) → **Hosting** → **Add custom domain**.
2. Enter **`civiconai.com`** (and optionally **`www.civiconai.com`**).
3. Add the **TXT** and **A/AAAA** records Firebase shows at your domain registrar (GoDaddy, Namecheap, etc.).
4. Wait for SSL (can take up to 24h; often minutes).
5. After the domain works, update:
   - **Cloud Run** `CORS_ORIGINS` to include `https://civiconai.com` and `https://www.civiconai.com` (full redeploy with all env vars).
   - **Maps browser key** referrers (below).

The default `*.web.app` URL keeps working; custom domain is an additional URL.

---

## Why Maps breaks on the live site (fix in Google Cloud Console)

The map uses **`VITE_GOOGLE_MAPS_API_KEY`** (browser key). It fails when referrers or APIs are wrong.

1. [APIs & Credentials](https://console.cloud.google.com/apis/credentials?project=inlaid-reactor-402513) → open the key used in `VITE_GOOGLE_MAPS_API_KEY`.
2. **Application restrictions:** HTTP referrers — add **all** sites you use.

   If the console shows **`RefererNotAllowedMapError`** and  
   `Your site URL to be authorized: https://inlaid-reactor-402513.web.app/`  
   you must allow that host on the **same key** as `VITE_GOOGLE_MAPS_API_KEY`:

   ```
   https://civiconai.web.app/*
   https://inlaid-reactor-402513.web.app/*
   https://inlaid-reactor-402513.firebaseapp.com/*
   https://civiconai.com/*
   https://www.civiconai.com/*
   http://localhost:5173/*
   http://127.0.0.1:5173/*
   ```

   Use the key named in Firebase/Vite (`VITE_GOOGLE_MAPS_API_KEY`), not the Weather server key.

3. **API restrictions:** enable at least **Maps JavaScript API** and **Places API** (if location search is used).
4. Save → wait 1–5 minutes → hard refresh the site (Ctrl+Shift+R).

Do **not** use the server weather key for Maps in the frontend.

---

## Why Weather breaks (fix on Cloud Run)

Weather uses **`GOOGLE_SERVER_API_KEY`** on the **API**, not in Firebase.

1. Enable [Weather API](https://console.cloud.google.com/apis/library/weather.googleapis.com?project=inlaid-reactor-402513).
2. Create or use a **separate** API key:
   - **Application restriction:** None (dev) or **IP addresses** (Cloud Run egress is not a fixed IP on default setup — often **None** + **API restriction = Weather API only** for server keys).
   - **API restriction:** Weather API only.
3. Cloud Run → **civicon-api** → **Edit & deploy new revision** → variable **`GOOGLE_SERVER_API_KEY`**.

Redeploy backend image only if code changed; env var change alone needs a new revision.

---

## CORS

`CORS_ORIGINS` on Cloud Run must list every frontend origin (comma-separated, no spaces), e.g.:

`https://inlaid-reactor-402513.web.app,https://civiconai.com,https://www.civiconai.com,http://localhost:5173`

Use **`gcloud run deploy`** with the **complete** `--set-env-vars` string when updating — partial updates can wipe other variables.
