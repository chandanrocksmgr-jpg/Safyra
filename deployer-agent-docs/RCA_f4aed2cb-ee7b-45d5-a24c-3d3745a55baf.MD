# RCA — Missing product images on https://safyra.co

## Problem statement
Live production site reports that **no product images render**. Asked to verify the event-loop redeploy completed, confirm `/api/products` returns 200, inspect live image_url/image_urls, check the HTTP status of each image, determine whether records still point at `https://safyra.co/cdn/shop/files/...` (Shopify CDN paths that now resolve to the Emergent app after DNS cutover), and check GridFS media + production logs. Diagnosis only — no DNS or catalogue changes made.

## Environment
- Deployment: `lucknowi-craft` (579fa11a-…), template farm_ts_react_mongo, kubernetes frontend, tier_0.
- Domains: `safyra.co` and `www.safyra.co` — both verified, pointing at the Emergent app.
- Active run: `f4aed2cb-ee7b-45d5-a24c-3d3745a55baf`.

## Findings (all evidence-backed)

### 1. Event-loop redeploy is complete and healthy
- `describe_deployment_state`: latest run `f4aed2cb` (type=redeploy) status **success**, completed 2026-10-18T15:13:19Z, and is the current `active_run_id`. No pending/failed run.

### 2. `/api/products` returns 200
- `preview_health_check` on `/api/products` → **200**, 523 ms, valid JSON.
- Backend logs show repeated `GET /api/products … 200 OK` (and `/api/homepage`, `/api/catalog-groups`, `/api/products/facets` all 200). No 5xx anywhere. (The `GET /health 404` lines are internal probe noise and unrelated.)

### 3. Every product still references Shopify CDN paths on the safyra.co domain
`products` collection holds **4** documents; **all 4** have `image_url` / `image_urls` pointing at `https://safyra.co/cdn/shop/files/...`:
- `sang-e-mar-mar-rose-edition`
  - `https://safyra.co/cdn/shop/files/preview_images/60cd79dc58734a6597c9712ff4d66366.thumbnail.0000000000.jpg?v=1766183317&width=1200`
  - `https://safyra.co/cdn/shop/files/136112B1-2A2D-4DF5-A6A7-E890FF9B97FF.jpg?v=1772205935&width=1200`
- `luxury-nazakat-collection`
  - `https://safyra.co/cdn/shop/files/BF92BEEC-84EB-497C-9B69-2948C142F272.jpg?v=1767270653&width=1200`
  - `https://safyra.co/cdn/shop/files/B774FE4A-8E49-49F8-9DB7-3B1A69457A93.jpg?v=1767270653&width=1200`
- `aira-pure-kota-doria-angrakha`
  - `https://safyra.co/cdn/shop/files/rn-image_picker_lib_temp_b45b8222-b248-4367-890e-33fce779156b.png?v=1768253915&width=1200`
  - `https://safyra.co/cdn/shop/files/IMG_3973.jpg?v=1772064171&width=1200`
- `vaaya-pure-kota-doria-anarkali`
  - `https://safyra.co/cdn/shop/files/rn-image_picker_lib_temp_5cea29bd-732e-4335-ba9f-0085b5624372.jpg?v=1772064200&width=1200`
  - `https://safyra.co/cdn/shop/files/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png?v=1780244603&width=1200`

### 4. Those image URLs now return HTML, not an image (THE root cause)
- `preview_health_check` on `/cdn/shop/files/BF92BEEC-84EB-497C-9B69-2948C142F272.jpg?v=1767270653&width=1200` →
  **HTTP 200**, but `content-type: text/html`, body is the React SPA `index.html` (`<!doctype html><html lang="en"> … SAFYRA CHIKANKARI …`).
- Why: before the DNS cutover, `safyra.co` pointed at Shopify and `/cdn/shop/files/...` served the real Shopify-hosted images. After the cutover, `safyra.co` resolves to the Emergent app. The app has **no `/cdn/shop/files/` route**, so nginx's SPA catch-all returns `index.html` (200 text/html) for every one of those paths. The browser `<img>` receives HTML instead of a JPEG/PNG → broken image. This affects **all 4 products / all 8 image references** identically.
- Note: requests to `/cdn/shop/files/...` never reach the FastAPI backend (served/handled by nginx), which is why no cdn/shop lines appear in backend logs.

### 5. No migrated media exists in GridFS
- GridFS collections `product_media.files` and `product_media.chunks` exist, but `product_media.files` **count = 0** — there are **no uploaded images** in the app's own storage to fall back to. So nothing currently serves these products' images from the Emergent side.

## Root cause
The product catalogue still references the **old Shopify CDN URLs under the store's own domain** (`https://safyra.co/cdn/shop/files/...`). Since the DNS cutover pointed `safyra.co` at the Emergent app — which has no such route — those URLs now resolve to the app's SPA fallback (HTTP 200, `text/html`) instead of the original images. No copies of the genuine images have been migrated into the app's GridFS store (it is empty), so every product image is broken.

## Safe fix (no DNS / no destructive catalogue edits)
The genuine images still live on Shopify's canonical CDN (`cdn.shopify.com/s/files/<shop-id>/files/<name>`), independent of the `safyra.co` domain — retrievable while the Shopify store/plan is still active. Recommended safe migration:
1. **Confirm the real source (User):** verify the Shopify store is still active and provide/confirm the canonical `cdn.shopify.com` URLs (or export the original image files) for each of the 8 referenced assets, so originals can be pulled before the Shopify plan lapses.
2. **Import + re-point (Code / E1):** add/verify a media-serving route backed by the existing `product_media` GridFS bucket, run a one-time migration that downloads each original from the canonical `cdn.shopify.com` path and stores it in GridFS, then rewrite `products.image_url` / `image_urls` to the app's own media URLs (e.g. `/api/media/<id>`). This preserves the genuine images and removes all dependence on the dead `safyra.co/cdn/shop/...` paths.
   - Do NOT blank out the catalogue URLs before the replacements are stored. Keep the originals until the GridFS copies verify.

## Verification notes
- Deployment / API health verified live (200s, no 5xx).
- Broken-image behavior verified live (200 `text/html` SPA fallback on a CDN path).
- GridFS emptiness verified via read-only Mongo query.
- The migration step was NOT reproduced in a sandbox — it requires live external fetches from Shopify's CDN plus DB writes, which the sandbox cannot do (no secrets / no external network for the real assets).
