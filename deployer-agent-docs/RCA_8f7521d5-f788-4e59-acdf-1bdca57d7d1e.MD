# RCA — Image upload failing on safyra.co ("IMG_9312.jpeg could not be uploaded")

## Problem statement
User uploads IMG_9312.jpeg from their phone via Admin > Products > gallery uploader on
live safyra.co; frontend shows generic toast "IMG_9312.jpeg could not be uploaded".
Reporter suspected an infra-layer failure (edge timeout, body-size limit, 502/504/499,
or the request never reaching FastAPI) because the generic toast was believed to appear
only when the fetch gets no valid HTTP response.

## Deployment / run
- Deployment: lucknowi-craft (579fa11a-...), domains www.safyra.co + safyra.co (both verified)
- Active run (HEIC fix): 8f7521d5-f788-4e59-acdf-1bdca57d7d1e — status success, frontend_type kubernetes (nginx in-pod), tier_0
- 2 healthy pods, ready, 0 restarts.

## Evidence
1. fetch_app_logs (run 8f7521d5, filter `media/upload`, last 1440 min) — exactly TWO upload requests:
   - `POST /api/media/upload HTTP/1.1" 201 Created`  (your direct HEIC test)
   - `POST /api/media/upload HTTP/1.1" 415 Unsupported Media Type`  (the user's phone upload)
   No 502 / 504 / 499 / 413 / timeout lines in the window (status histogram: 200x1, 201x1, 415x1, 404x5 health probes).
2. get_pod_events (run 8f7521d5) — both pods Running, ready=true, restart_count=0. No OOM, no CrashLoop, no evictions. (Only noise: startup-probe 503s during the initial rollout boot on 2026-11-01, long since healthy.)
3. The `201` proves a multipart image upload traverses Cloudflare -> nginx -> FastAPI cleanly in this exact window and edge path — so there is NO upstream read/write timeout and NO body-size (413) rejection on this route. nginx has no manifest override (platform default) and did not need one here: the 201 is empirical proof the path passes images.

## Why the 415 happens (app code — backend/routers/media.py)
The 415 is raised by the app itself, not the edge. Relevant validation:
- ALLOWED_TYPES = {"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}; FORMAT_TYPES = {"JPEG","PNG","WEBP"}
- After PIL opens the file, the non-HEIF branch does:
  `detected_type = FORMAT_TYPES.get(image_format)`
  `if not detected_type or detected_type != file.content_type: raise HTTPException(415, "The image format does not match its file type")`
- Pre-check (line 73): `if file.content_type not in ALLOWED_TYPES and not is_heif_upload: raise 415 "Upload a JPG, PNG, WebP or iPhone HEIC/HEIF image"`

A phone JPEG named IMG_9312.jpeg most likely hits one of two app-level branches:
  (a) **MPO format** — iPhone HDR / Live-Photo JPEGs are Multi-Picture-Object JPEGs; PIL reports `image.format == "MPO"`, which is NOT in FORMAT_TYPES, so `detected_type` is None -> 415 "The image format does not match its file type". (Strongest candidate.)
  (b) **content-type variant** — mobile Safari/Android sending `image/jpg` (not `image/jpeg`) fails the ALLOWED_TYPES pre-check -> 415 "Upload a JPG, PNG, WebP...".
I could not byte-level reproduce the exact branch in the eph sandbox (Pillow/pillow_heif not installed in the source-only checkout), so the specific branch is INFERRED; the fact that the failure is an app-level 415 (not infra) is PROVEN from production logs.

## On the generic toast (correcting the original hypothesis)
frontend/src/lib/api.ts `apiUpload` DOES parse the JSON error body and throws `ApiError(status, body)`
for any non-2xx. ImageManager.tsx errorDetail() then returns `body.detail` and shows
`"<file>: <detail>"`. So a backend 415 (which returns `{"detail": "..."}`) should surface the
SPECIFIC message, not the generic fallback. The generic "could not be uploaded" fallback only
fires when the thrown error is NOT an ApiError with a string detail — i.e. a true fetch()
rejection (no HTTP response) OR a 415 whose body didn't parse as JSON.
=> The toast text alone cannot prove "never reached the backend." Production logs show a clean
415 that DID reach FastAPI, which contradicts the network-failure reading for the request we can
see. If the user also had a separate attempt that genuinely failed at the network layer (which
would be invisible in backend logs), that would be a client/cellular drop, not a server-side
infra fault — nothing on our edge/pods shows a failure.

## Root cause
Application-level media-type validation in backend/routers/media.py rejects the user's iPhone
JPEG with HTTP 415. The infra layer (Cloudflare, nginx ingress, k8s pods) is healthy — proven by
a concurrent successful 201 image upload and clean pod state. The reported infra symptoms
(edge timeout / body-size / 502-504-499) are NOT present in logs.

## Suggested fixes
1. CODE (E1):
   - Broaden upload validation in backend/routers/media.py to accept iPhone JPEG variants:
     treat `image.format == "MPO"` as JPEG (add to FORMAT_TYPES / normalize MPO->image/jpeg),
     and normalize `image/jpg` -> `image/jpeg` before the ALLOWED_TYPES check. Relax the strict
     `detected_type != file.content_type` equality so a valid JPEG/PNG/WEBP isn't rejected purely
     on a declared-vs-detected mismatch.
   - Reproduce with a real iPhone HDR/Live-Photo JPEG (not a plain re-saved JPEG) to confirm the
     MPO branch before shipping.
   - Optional UX: ensure the 415 detail reaches the toast (it should today) so users see the real
     reason instead of the generic fallback.
   Requires a redeploy after the code change.
2. USER (test_and_verify): after E1 ships the fix and redeploys, re-test the same IMG_9312.jpeg
   from the phone. If a failure still shows the GENERIC toast with NO corresponding backend log
   line, capture the request in mobile DevTools (status / response body) so we can confirm whether
   any attempt is failing before reaching FastAPI (vs. the app-level 415 proven here).
