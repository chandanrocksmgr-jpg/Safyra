# SAFYRA CHIKANKARI — Living Spec

## Purpose
Premium, mobile-first editorial ecommerce experience for handcrafted Lucknowi Chikankari. The build is independent of Shopify and uses a Mongo-backed approved catalog that SAFYRA staff can maintain through `/admin`.

## Brand system
- Warm Ivory `#F7F3EB` is the dominant canvas, Deep Espresso `#261C19` is the primary UI dark, and Deep Aubergine `#49343D` is reserved for sparse editorial accents.
- Cormorant Garamond is the display/editorial typeface; Manrope is used for body copy, navigation, commerce UI, product names, prices and controls.
- Functional WhatsApp, success, warning and error colours remain intact for usability.

## Core flows
- Home: rotating announcement messages, product-led hero, immediate new arrivals, five-card category discovery without number overlays, conditional verified bestsellers, SAFYRA Luxury, collections, a five-story verified customer carousel, concise Lucknow story and WhatsApp care.
- Navigation: Shop by Category permanently retains the approved eight-category contract—Anarkalis, Angrakhas, Kurtas, Stitched Sets, Sarees, Dupattas, Chikankari Bottoms and Unstitched Sets. Empty approved categories remain visible and route to an honest editorial empty state until genuine products are assigned.
- Shop: instant search suggestions and recent searches; combinable category, collection, size, colour, fabric, craft, availability and price filters; supported sorting; zero-result recovery.
- Product: real product-only galleries with zoom/swipe, required size selection, verified-only expandable details, add to bag, Buy Now to checkout preparation, contextual WhatsApp, custom-dyeing enquiry only when the stored customisation field explicitly supports dyeing, admin-approved Complete the Look, relevant recommendation groups and mobile sticky add.
- Product detail pages also include a genuine-image “A closer look” section, above-fold fabric/work/dispatch facts, clean breadcrumb URLs, dynamic titles/meta/canonical links and Product structured data.
- Shop and collection states publish dynamic titles, descriptions, canonical links and ItemList structured data; home publishes WebSite search structured data.
- Wishlist and cart: guest state persists in browser local storage; signed-in customer state persists to the account in Mongo. Cart drawer and full cart page include quantities and contextual WhatsApp order handoff.
- Customer account: email/password and Emergent-managed Google sign-in, profile editing, saved wishlist/cart continuity, verified exact-email guest-order claiming, prior paid-order history, GST PDF access when legally configured, courier links and Confirmed → In production → Quality check → Shipped → Delivered tracking. Google links to an existing customer by email and never grants Admin access. No demo customer or fabricated order is seeded.
- Admin: hidden from storefront navigation, server-protected by the admin role, and available at `/admin-login`. `/admin/products` adds/edits complete catalogue records; `/admin/collections` controls approved categories/edits; `/admin/homepage` controls fixed-layout content; `/admin/offers` runs scheduled non-stacking coupon or automatic discounts with scope, minimum spend and usage limits; `/admin/analytics` reports paid revenue, AOV, units, checkout-to-paid conversion, abandonment, products and offers; `/admin/settings` holds GST invoice configuration and safe sample previews.
- Admin order management: protected `/admin/orders` lists/searches/filters requests, guards PayU status, manages the five-stage customer tracking flow, courier links, internal notes, refunds, cancellation, GST invoice/credit-note access, manual WhatsApp previews and append-only history. Fulfilment emails are idempotent and contain no unverified courier link.
- Customer waitlist: genuinely unavailable products offer a “Limited availability · Join the waitlist” modal. Name and mobile are required, email is optional, size is required only when the product has configured sizes, and colour is requested only when multiple configured colours exist. Single configured colours are recorded automatically; no size or variant is invented.
- Admin waitlist management: protected `/admin/waitlist` supports customer/product search, lifecycle filtering, detail review, internal notes and Waiting → Contacted → Converted / Closed status tracking.
- Checkout: guest-friendly validated address capture with searchable country/state/city suggestions, country-aware phone/postal validation and cart-note persistence. India orders are server-priced, charged ₹120 shipping through ₹999 and receive free shipping from ₹1,000, then redirect to PayU Hosted Checkout. International orders remain WhatsApp-assisted requests with shipping confirmed personally before payment.
- Abandoned checkout recovery: checkout activity is upserted only after a valid name and email/mobile are entered, remains In progress for 30 minutes, becomes Abandoned after inactivity, and links to the resulting order request on completion. A protected `/admin/abandoned-checkouts` workspace exposes captured details, completion state, internal activity and recovery-email status.

## Data model
`Product`: id, title, slug, category, collection, fabric, craft, price, optional verified mrp, stock, stock_by_size, approved sizes/colours/images, optional verified description/specifications, origin, occasion/style search terms, size-guide image, availability, merchandising flags, Draft/Active/Archived status and admin-approved complete-look product IDs. Only Active (or legacy status-less) products are public.

`CatalogGroup`: id, name, slug, group_type (`category` or `collection`), description, image_url, Draft/Active/Archived status, sort_order and show_on_home. Product assignments remain string-based for compatibility with the existing catalogue. The eight approved category destinations are restored idempotently even when some contain no current products.

`HomepageSettings`: one `homepage` document containing announcement messages, fixed-layout hero content, section visibility and headings, brand-story content/images and WhatsApp section copy. Customer pages always retain local SAFYRA defaults if the content API is unavailable.

`MediaUpload`: protected Admin multi-file uploads accept validated JPG, PNG and WebP files up to 8 MB each, persist binary data and metadata in Mongo GridFS, and return immutable same-origin `/api/media/...` URLs. Product galleries support up to 40 images with reordering and a "Make primary" (star) action. Product create/update rejects image links that are not `https://`, `http://` or `/api/media/...` (e.g. WhatsApp `blob:` links), and the admin URL field warns before adding them. Saving a product invalidates both the `["products"]` lists and `["product", id]` detail caches.

`Legacy Shopify media`: after the DNS cutover, `safyra.co/cdn/shop/files/...` no longer reaches Shopify. `GET /api/media/shopify/{path}` serves the original from GridFS (metadata.legacy_path), fetching it once from `cdn.shopify.com/s/files/1/0853/1325/7781/files/{path}?width=1600` on first request. A startup background task (`lib/legacy_media.migrate_legacy_media`, idempotent) rewrites legacy URLs in products, site_content, catalog_groups, order_requests, checkout_sessions and orders to `/api/media/shopify/...`, removes device-only links from product galleries, and pre-caches every referenced file. Storefront `SafeProductImage` falls back through the gallery when one image fails and retries whenever the source list changes.

Mongo lifecycle: the shared database handle is loop-safe and creates Motor inside the active FastAPI/seed event loop. Production ASGI module import never creates a Motor client, preventing cross-event-loop `Future attached to a different loop` failures while preserving the existing router-level `db` API.

`OrderRequest`: id, request_number, received_at, optional customer_id, validated contact/delivery fields, customer note, server-priced product items, discounts, shipping and total. International records remain unpaid requests; India PayU records move from Payment pending to Confirmed only after a verified gateway webhook or reconciliation response.

`StoreSettings`: one Admin-only legal/tax configuration document with SAFYRA legal name, GSTIN, registered address, seller state/code, transaction-value GST slabs, the two approved product HSN codes, support contacts, authorised signatory and atomic invoice/credit-note sequences. Invoice GST is tax-inclusive and calculated per item at 5% when its actual selling price is at or below ₹2,500, and 18% above ₹2,500, effective under the user-confirmed post-22-September-2025 apparel rule. Previews are watermarked `SAMPLE - NOT A TAX INVOICE`.

Current configured tax identity: `SAFYRA CHIKANKARI`, GSTIN `09BGVPH9614M1ZH`, `Husainabad, Lucknow, Uttar Pradesh 226003`, state code `09`, support `safyrachikankari@gmail.com` / `+918090164929`, authorised signatory `Afira`. Product HSN is snapshotted at checkout: `62063090` for cotton woven kurtis/tunics and `62114922` for other women’s Chikankari garments.

`Invoice`: immutable seller, buyer, item, tax and total snapshot linked uniquely to a paid order. PDF is generated on demand and is accessible only to Admin or the verified owning customer. Credit notes are generated only for confirmed refunds and remain Admin-only.

`WaitlistRequest`: id, product snapshot, required customer name/mobile, optional normalized email, applicable configured size/colour, status, internal notes and timestamps. Active Waiting/Contacted requests are deduplicated for the same product and applicable variant when either normalized mobile or email matches. Converted/Closed requests release the active duplicate lock so the customer may join again later.

`CheckoutSession`: stable session key, checkout reference, captured contact/address snapshot, server-priced items, In progress/Abandoned/Completed status, linked order request, one-email reminder state and internal activity. Session-key upserts prevent duplicate checkouts while order linkage permanently suppresses recovery sends.

Stock enforcement: currently-unavailable products cannot be purchased; made-to-order products are not blocked by zero on-hand stock; other products use selected-size stock when present and otherwise global stock. The same rule is rechecked when an order request is submitted.
Published products that this existing rule determines to be genuinely unavailable display “YOU MISSED IT” on product cards and product detail pages, with purchase controls disabled. Made-to-order sizes remain selectable regardless of zero on-hand stock.
The waitlist API independently rechecks genuine unavailability and configured variants before accepting a request; available products, invalid sizes/colours and active duplicates are rejected server-side.

## Trust and accuracy
The public catalog contains only the four products captured from the approved prior SAFYRA data pull: Nazakat, Aira, Vaaya and Sang-e-Mar-Mar. Test/debug and unapproved placeholder products are removed. Product names, public prices, genuine compare-at prices, known fabrics, craft details and dispatch windows are grounded in the stored approved data. Empty or unverified fields are omitted. No percentage discounts, ratings, review quotes, customer counts, urgency timers or invented public stock claims are shown.

## Auth
Authentication uses a random opaque token in a secure, httpOnly cookie. Only the SHA-256 token digest is stored server-side; passwords and the admin recovery answer use salted PBKDF2-SHA256. Email/password customer login and separate Admin login remain active. Emergent Google Auth is live on Login and Signup ("Continue with Google", flag `GOOGLE_SIGN_IN_ENABLED` in frontend/src/lib/features.ts). The auth host answers with an S3 404 status while still rendering its sign-in app (browsers then reach Google), and session-data returns 404 `user_data_not_found` for invalid or reused session IDs; both are expected. See /app/auth_testing.md. Checkout shows guests a "Returning to SAFYRA?" block with Continue with Google (returns to /checkout, then the default saved address auto-fills) plus an email sign-in link. On the first account sync after any sign-in, ShopProvider merges the guest bag (max quantity per line) and wishlist (union) into the account instead of replacing them; `safyra-cart-owner` in localStorage records which account the local bag belongs to. Google can never authenticate an Admin. Customer email confirmation uses hashed, expiring, one-time links. Logout clears the server session and full query cache.

## Integrations
Emergent-managed Resend sends fixed SAFYRA templates for account verification, first-time Google account linking, abandoned-checkout recovery, order/request and verified-payment messages, invoice-ready notifications, and idempotent In production/Quality check/Shipped/Delivered updates. PDFs are not attached because the managed proxy does not expose attachments; the GST PDF remains in verified My Account. Provider billing/integration failures are recorded without breaking account creation. Platform crons retry queued order/status sends. No WhatsApp or marketing messages are automated.
PayU India Hosted Checkout uses server-only Live Key/Salt hashing, verified reverse hashes, amount/key/transaction checks, webhook confirmation, 15-minute reconciliation and idempotent automatic order conversion. Payment details never enter SAFYRA. In-stock inventory is reserved before redirect and released after failed/expired payment; made-to-order pieces do not consume stock. PayU is enabled only for India; international orders remain personally quoted. Each payment stores its validated current HTTPS origin, so callbacks return to preview, the deployed host or `safyra.co` without a stale-domain configuration switch.
No courier-label API is integrated. Manual courier name, tracking number/link and shipping notes remain unchanged and must not be represented as a generated courier label.

## Variant inventory (Shopify-style)
- `products.set_types` = admin-defined **combinations** (e.g. Kurta only, Kurta + Dupatta), each `{id, name, price, mrp}`; optional per product, never auto-created.
- `products.variants` = one row per combination × colour × size: `{id, set_type_id, color, size, price?, mrp?, stock, available}`. Empty string = dimension not used. Price falls back variant → combination → product.
- When `variants` is non-empty it is the single source of truth for stock for **every** availability label (made to order included). `stock` / `stock_by_size` are mirrored totals only. Products without variants keep the legacy size-level behaviour.
- Backend keeps the table aligned with options on every create/update (`lib/variants.align_variants`): removed options drop rows, new combinations get 0 stock. Startup migration `migrate_product_variants` created rows for existing products (carried over their stock, which was 0).
- Checkout: `price_order_items` blocks sold-out or switched-off variants (409 naming the exact variant); `/payments/create` reserves with an atomic `$inc` on `variants.$.stock` guarded by `stock >= qty` and `available`; failures and cancellations release it.
- Storefront: product page has a combination picker plus crossed-out sold-out colours and sizes. Selecting a sold-out variant swaps Add to bag for "Notify me when available", which opens the waitlist prefilled with that variant. Cards show "From ₹…" when prices differ. Bag, checkout, orders, invoices, emails and WhatsApp messages show "Combination · Size · Colour" (`variantLabel`).
- Waitlist is per variant (`set_type` stored and part of the duplicate key). Each new request emails the store's support email (falls back to the admin login) via Resend.
- Admin: Products editor → "Options, variants & inventory" → Combinations list + Variants table (filters by combination/colour/stock, bulk "Set for N shown", per-row price, stock, Available switch, status).
- Test note: older tscheck tests that buy the real catalogue (checkout/shipping/offers) expect made-to-order pieces to always be purchasable. With variant inventory at 0 they correctly get 409 "… is sold out" until the admin enters stock. `test_admin_can_create_update_and_delete_product` also fails on its own because it logs in as the removed demo `customer@safyra.co` account (unrelated to inventory).

## SAFYRA Credit (store credit for returns)
- Admin → **Customers** (`/admin/customers`): search registered customers by email, mobile (any format, digit match) or name. The detail view shows balance, each credit (issued, amount, remaining, valid until, Active/Used/Expired), full history and orders. "Issue credit" takes any whole-rupee amount, asks for confirmation, and emails the customer (Resend) with the amount and expiry.
- Data: `store_credits` grants `{id, customer_id, amount, remaining, issued_at, expires_at (= issued_at + 1 year), issued_by}` and `store_credit_activity` `{type: issued|redeemed|restored, amount, request_number}`. Balance = sum of `remaining` on unexpired grants.
- Checkout (signed-in customer, India): "Use my SAFYRA Credit" checkbox (pre-ticked). `/payments/quote` and `/payments/create` take `use_store_credit`; `credit_applied = min(balance, total)` and covers products, GST and shipping; `amount_due = total - credit_applied` is all PayU collects. Orders keep `total` = full order value.
- Credit is **held** at `/payments/create` (soonest-expiring grants first, atomic per grant, rolled back if short). Allocations are stored on the order request (`credit_allocations`, `credit_status` held → redeemed | restored). PayU success marks it redeemed. Failure, expiry or a superseded attempt restores it exactly once.
- `amount_due == 0` → no PayU: payment_provider "SAFYRA Credit", confirmed immediately (`_mark_paid`), invoice generated, `completed: true` returned, and the frontend goes to `/payment-result`.
- GST invoice: credit is a payment method; taxable value and GST stay on the full total. The PDF adds "Paid via SAFYRA Credit" and "Paid online (PayU)" rows, and emails show the split.
- On payment confirmation the purchased lines are removed from the customer's saved bag server-side (prevents the bag reappearing after payment).
- Fix: account `Order` snapshots coerce null courier/tracking/invoice fields to "" (previously `/api/account` returned 500 after a customer's first confirmed order).

## Password reset (customer email login)
- `/login` shows "Forgot password?" → `/forgot-password` (`POST /api/auth/password-reset/request`). Response is always generic (`{accepted:true}`) so account existence is never revealed; max 5 requests per email per 15 minutes.
- Token: 40-byte urlsafe, stored only as SHA-256 in `password_reset_tokens` `{token_hash, user_id, email, created_at, expires_at, used_at}`. **Single use, 10-minute expiry.** Requesting again deletes the previous unused token.
- Email (Resend) links to `/reset-password?token=…`. `POST /api/auth/password-reset/confirm {token, new_password}` validates strength, sets the hash, adds "password" to `auth_providers` (Google-only accounts can gain a password), deletes all sessions, 204. Invalid/expired/reused token → 400.
- Frontend pages: `pages/ForgotPassword.tsx`, `pages/ResetPassword.tsx`. After a successful reset the user is sent to `/login`.

## Invoices are tax-free documents (no GST)
- Invoice/credit-note PDFs no longer print any tax content: title is "INVOICE"/"CREDIT NOTE", no GSTIN, no HSN/GST/Taxable columns, no CGST/SGST/IGST rows, no place-of-supply or reverse-charge lines, footer is "Computer-generated document.". Totals = Product subtotal, Shipping, Total (+ SAFYRA Credit / PayU split).
- `REQUIRED_INVOICE_FIELDS` now only gates on registered address, seller state, support email/phone and authorised signatory. GST fields remain in store settings and are still stored on invoice documents, but are never rendered.
- Storefront "Taxes included" notes removed from product, cart and checkout; emails and admin copy say "invoice", not "GST invoice".

## Colour options (swatches, per-colour photos)
- `products.color_options` = `[{name, swatch, image_urls}]`, same names and order as `products.colors` (names stay the key used by variants, cart, filters and search). Backend `lib/colors.py` normalises on every create/update: de-duplicates names, auto-fills the swatch from the colour name (keyword palette + stable muted fallback, mirrored in `swatchFor` in `lib/shop.ts`), and drops assigned photos that are no longer in the product gallery. `migrate_color_options()` backfilled existing products at startup.
- Product page: swatch row under the gallery shows the colour's first assigned photo as a thumbnail, or the hex swatch when no photo is assigned. Selecting a colour swaps the gallery to that colour's photos (`galleryFor`, falls back to the whole gallery), resets to the first image, and the size grid re-reads variant stock for that colour (sold-out sizes cross out and offer "Notify me").
- Admin → Products → Options, variants & inventory → **Colours** (`components/ColorManager.tsx`): add/rename/remove colours, edit or auto-reset the swatch with a colour picker, and tick which gallery photos belong to each colour. Renaming a colour renames its variant rows (stock preserved); removing one deletes its rows. Colour names must be unique and non-empty.
- Fix: the admin "Size guide image URL" field was `type="url"`, which blocked saving any product whose size guide is an uploaded `/api/media/...` path.

## New-order alerts for the admin
- Fires once per order, only after payment is verified (`_mark_paid` → `notify_admin_new_order` in `lib/admin_alerts.py`), for both PayU and full SAFYRA Credit payments. Idempotent via a unique index on `admin_order_alerts.request_id`.
- Email: order number, customer, items, shipping, total (credit split noted) and an "Open the order" button, sent through Emergent Resend to `ADMIN_ALERT_EMAIL` (backend/.env, currently safyrachikankari@gmail.com).
- In-panel: `components/AdminOrderAlerts.tsx` is mounted in `AdminRoute`, so it shows on every admin page. It polls `GET /api/admin/order-alerts` every 15s, lists pending alerts bottom-right and clears them through `POST /api/admin/order-alerts/ack` (`alert_ids: []` dismisses all; opening an order acks just that one).
- Sound: WebAudio — a soft two-note chime first, then a louder three-note alert repeating every 9s while any alert is pending. Mute toggle in the banner header, remembered per device in `localStorage["safyra-order-alert-muted"]`.

## Daily order digest (9pm IST)
- Cron `order-digest` in `.emergent/crons.yml`: `0 21 * * *` in `Asia/Kolkata` → `POST /api/cron/order-digest` (Bearer `WEBHOOK_CRON_SECRET`, acks 202 and backgrounds the work, `X-Webhook-Id` deduped through `cron_runs`).
- `routers/order_digest.py` emails `ADMIN_ALERT_EMAIL`: today's paid orders (IST day window via `lib/dates.now_in_app_tz`), revenue, pieces sold, SAFYRA Credit settled, a per-order list, and a consolidated "pieces to pack" list (title · set · size · colour × qty with order numbers) for every paid order still in Confirmed / In production / Quality check / Ready to dispatch.

## Colour dots on shop cards
- `ProductCard` shows up to 5 colour dots (the colour's first assigned photo, else its swatch) with a `+N` overflow, only when a product has more than one colour. Each dot links to `/product/{slug}?color={name}`, and the product page pre-selects that shade from the `color` query param.

## Role-based access control (Super Admin / Junior Admin)
- Staff accounts are `users.role == "admin"` with `admin_role` = `"super"` or `"junior"` and `status` = `"active"` / `"deactivated"`. Legacy admins were migrated to super/active at startup.
- `lib/security.py`: `require_admin` = any active staff; `require_super_admin` = super only; `get_current_user` kills the session of a deactivated account, and `_login` refuses it with 403.
- Junior Admins reach only the products API (`routers/products.py`) and media uploads (`routers/media.py`). Everything else — order_requests, store_credit/customers, checkout_sessions, discounts, waitlist, analytics, store_settings, homepage, catalog_groups writes, admin_alerts, order_digest, staff and information writes — is `require_super_admin`, and invoices require `is_super_admin`. Verified: a junior session gets 403 on every one of those and 200 on products.
- `routers/staff.py` (`/api/admin/staff`, super only): list, create (hard-coded to junior — no API path creates or promotes a super), rename, activate/deactivate (deletes the account's sessions), reset password, delete. Super Admin rows are rejected by `_junior()` so they can never be demoted, deactivated or deleted through the API.
- Frontend: `User.admin_role` drives everything — `SuperAdminRoute` bounces juniors to `/admin/products`, `AdminShell` hides non-catalogue nav, the dashboard hides order/waitlist metrics and cards, and the new-order alert widget only mounts for supers. Admin → Staff access = `pages/AdminStaff.tsx`.

## Editable care & information page
- `GET /api/information` is public, `PUT /api/information` is Super Admin only (`routers/information.py`, defaults in `DEFAULT_CONTENT`, stored in `site_content` under id `information`).
- Editable: eyebrow, two-line headline, intro, every section (tab label, anchor id, headline, body — add/remove), FAQ heading and Q&A pairs (add/remove), and the WhatsApp button label plus its pre-filled message. Admin screen: `pages/AdminInformation.tsx` at `/admin/information`; the storefront page reads it live.

## Combination pricing + per-variant override
- In the product editor's variant table, filter by combination (and/or colour/stock), enter a price and press **Price N shown** → a preview panel lists old → new for up to 8 rows and the total count; nothing changes until **Apply** is pressed. This is how a new product gets one price per combination (Kurta only, Kurta + Dupatta, …) across every size and colour at once.
- Any single variant can still be overridden in its own Price cell, and **Clear overrides** resets the shown rows back to the combination/product price (blank = inherit). Verified: bulk 4,199 applied to 35 variants, then Blush petal · M overridden to 4,599, both persisted.

## Editable About page
- `GET /api/about` public, `PUT /api/about` Super Admin only (`routers/about.py`, `site_content` id `about`). Editable: eyebrow, two-line headline, intro, hero image, craft/artisan story blocks (heading, body, image — add/remove), "Why SAFYRA" promises, founder block (name, role, pull quote, note, portrait) and the WhatsApp prompt.
- Storefront page `/about` (`pages/About.tsx`) replaces the old `/information#craft` header link; admin screen `/admin/about` (`pages/AdminAbout.tsx`, nav "Brand story").

## Out-of-stock wording
- The stored availability value is still `"Currently unavailable"`, but every customer- and admin-facing surface renders it through `availabilityLabel()` in `lib/shop.ts` as **"You just missed it"** — product page badge, availability line, accordion, Add-to-bag button, shop cards, shop availability filter, and the admin product list and availability dropdown.

## Order numbering (financial-year series)
- `lib/order_numbers.py`: `SAF{FY}{NNNNNN}` → e.g. `SAF26-27000001`. FY label is the Indian financial year in APP_TZ (1 Apr – 31 Mar), and the 6-digit counter lives in `counters` under `order-number-{label}`, incremented atomically, so it restarts at 000001 every 1 April. Used by both `/api/order-requests` (international) and PayU checkout. Older `SAF-REQ-…` numbers stay valid on existing orders.

## Product videos
- `products.video_urls` holds up to 2 URLs (Pydantic + TS both capped at 2; a third is rejected with 422). `POST /api/media/upload-video` (admin) accepts MP4/WebM/MOV up to 40 MB into the same GridFS bucket and is served by `GET /api/media/{id}` with its real content type; a link can be pasted instead.
- Admin: `components/VideoManager.tsx` inside the product media card. Storefront: an "In motion" section on the product page renders the films with native controls.

## Combination pricing (clarified)
- Pricing is per **combination within one product** (set type), never per collection: each combination row has "Price all its variants", which previews and then applies that combination's price to every colour and size of it. The variant toolbar's "Price N shown" does the same for whatever the filters show. Individual variant prices remain editable as overrides.

## Invoice & credit-note numbering (financial-year series)
- Invoices are `INV26-27000001` and credit notes `CN26-27000001`, generated by `next_document_number(prefix)` in `lib/order_numbers.py` — the same atomic per-financial-year counters (`counters` collection) used for order numbers, restarting at 000001 every 1 April. The old `invoice_prefix` / `invoice_next_number` store-settings fields are no longer used for numbering.

## Video cover stills
- `products.video_posters` (max 2) holds one poster per film, aligned by index with `video_urls`.
- On upload, `components/VideoManager.tsx` captures a frame client-side (canvas grab at ~1s), uploads it through `/api/media/upload` and sets it as the cover; the admin can instead pick any gallery photo as the cover, and a pasted video link defaults to the first gallery photo. The storefront player falls back to the first gallery image if no poster is set.

## First-order gift offer
- Settings live in `site_content` id `gift_offer` (`routers/gift_offer.py`): `enabled`, `threshold` (default ₹5,000), `product_id`, headline, subtext, terms. `GET /api/gift-offer` is public; `GET/PUT /api/gift-offer/settings` and `GET /api/gift-offer/products` are Super Admin only. Enabling without an active gift, or choosing a product not marked as a gift, is rejected with 422 — so exactly one gift can be live and the offer can be paused and restarted at will.
- Gift products are ordinary products with `is_gift: true` (ticked in Products → Merchandising, usually with category "Gift"). They are filtered out of the shop list, facets, product detail and `PUBLIC_PRODUCT_FILTER`, so they can never be browsed or bought directly (422).
- `lib/gift_offer.gift_item_for_order()` appends a ₹0 gift line (`is_gift: true`) to the order at creation in both checkout paths (PayU and international requests) when: the shopper is signed in (registered), the offer is enabled, the bag subtotal ≥ threshold, and `order_requests` holds no earlier non-cancelled order for that email/customer. The order also records `gift_product_id`. Gift stock is not reserved — the admin watches the gift's own stock.
- Storefront: `GiftOfferPopup` (first visit per device, remembered by gift id in `localStorage["safyra-gift-offer-seen"]`) shows the headline, the gift and its terms; `GiftCartNotice` on the cart and checkout calls `GET /api/gift-offer/eligibility?subtotal=` and shows "add ₹X more" / "sign in" / "is on us". Admin screen: `/admin/gift-offer`.
- The header account (sign-in) icon is now visible on mobile as well as desktop.

## Site icon
- The template's default Emergent favicon was replaced with a SAFYRA mark (chocolate tile, ivory serif "S"): `favicon.svg`, `favicon.ico`, 16/32px PNGs, `apple-touch-icon.png`, plus `icon-192.png` / `icon-512.png` referenced from `index.html` (Google prefers a large square icon) and used as `og:image`. The app itself has never contained a "Made with Emergent" badge. The live domain keeps serving the old icon until the next publish, and Google refreshes it on its next crawl.

## Gift stock control & gift in documents
- Granting a gift now **claims one piece atomically** (`$inc stock -1` guarded by `stock >= 1`). If the gift is out of stock no gift is added, and eligibility replies "This gift is fully claimed for now."
- `low_stock_threshold` (default 5) in the gift settings: when a claim leaves the gift at or below it, `notify_low_gift_stock()` emails `ADMIN_ALERT_EMAIL` (once a day, always when it hits zero, deduped by `site_content.gift_offer.low_stock_alert_date`). The admin screen also shows a red banner ("Only N left" / "is out of stock") and each gift card shows its stock.
- The gift appears as a line in customer documents: the request-received email tags it "Complimentary gift" with the amount shown as Free, the payment-confirmed email adds a "With our compliments" line, and the invoice PDF prints the item with "Complimentary first-order gift" and Free in the price columns (so the total is unaffected).

## Gift offer: announcement without a chosen gift (bug fix, Oct 2026)
- The live site reported "no popup on the landing page" after publishing: production has its own database where the offer had never been enabled and no gift product existed. The popup required `enabled && product`, so it stayed hidden.
- Fix: `PUT /api/gift-offer/settings` now accepts `enabled: true` with an empty `product_id` (a non-gift product id is still 422), the popup renders with a gift-box placeholder and no product line, eligibility reports "the gift for this offer is being chosen", and the admin screen shows `admin-gift-no-product` while the announcement runs without a gift. Gift lines still only attach when a gift product is active and in stock.
- Production data must still be switched on in the live admin (Admin → Gift offer) or via the live API after each fresh environment.

## Media upload limits
- Product images: effectively unrestricted — `MAX_BYTES` is 200 MB (was 8 MB) and Pillow's decompression guard is 200 MP; videos stay at 40 MB.
- Auto-optimisation (`_optimised()` in routers/media.py): an upload over 6 MB or longer than 4000 px on its long edge is EXIF-rotated, capped at a 4000 px long edge and re-encoded (JPEG q92 progressive; PNG/WebP keep their format), and the response carries a "Optimised from N MP…" note. JPEG decoding uses `draft()` so a 100 MP original is never expanded at full size in memory. Smaller photos are stored byte-for-byte, and if the re-encode is not smaller the original is kept. Verified: an 80 MP / 21 MB JPEG stored at 3200×4000 / 8.9 MB; a 30 KB photo untouched.

## Saving a product as Draft (no photo/price yet)
- A product can now be created or updated with `status: "draft"` even with no photo and ₹0 price — the client no longer hard-blocks submission on a missing image, and the backend's primary-image validator accepts blank for any status. This is the actual "save progress" a WIP product gets server-side (shows up in Admin → Products with the Draft pill), distinct from the separate per-browser localStorage autosave/resume that already existed.
- Switching a product to **Active** (create or update) is blocked with 422 unless it has a real photo (`image_url`) and a price above ₹0 — enforced in `routers/products.py` (`PUBLISH_REQUIRES_PHOTO` + a price check) and mirrored client-side (Price field only HTML-required when Status = Active).
- Slug conflicts on create/update now name the exact existing product holding that slug instead of a generic message.

## Bulk photo upload
- `ImageManager` accepts a whole shoot dropped anywhere on the gallery panel (dashed highlight while dragging) as well as the existing multi-select "Upload images" button and single URL paste; a live "Uploading n of N…" counter runs during the batch.
- Tiles are drag-and-drop reorderable (HTML5 draggable, drop on the tile you want to take that position) alongside the existing move-up/move-down/make-primary buttons. Verified: three photos dropped at once, then the third tile dragged to Primary.
- Fix: `label.admin-upload-button.button-dark` had dark-on-dark text (inherited form-label colour), which made "Upload images"/"Upload video" invisible.
