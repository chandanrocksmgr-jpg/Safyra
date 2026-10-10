# SAFYRA CHIKANKARI — Living Spec

## Purpose
Premium, mobile-first editorial ecommerce experience for handcrafted Lucknowi Chikankari. The build is independent of Shopify and uses a Mongo-backed approved catalog that SAFYRA staff can maintain through `/admin`.

## Brand system
- Warm Ivory `#F7F3EB` is the dominant canvas, Deep Espresso `#261C19` is the primary UI dark, and Deep Aubergine `#49343D` is reserved for sparse editorial accents.
- Cormorant Garamond is the display/editorial typeface; Manrope is used for body copy, navigation, commerce UI, product names, prices and controls.
- Functional WhatsApp, success, warning and error colours remain intact for usability.

## Core flows
- Home: rotating announcement messages, product-led hero, immediate new arrivals, five-card category discovery without number overlays, conditional verified bestsellers, SAFYRA Luxury, collections, a five-story verified customer carousel, concise Lucknow story and WhatsApp care.
- Navigation: Shop by Category and Shop the Edit groups route to future-ready catalogue URLs without creating or modifying catalogue data.
- Shop: instant search suggestions and recent searches; combinable category, collection, size, colour, fabric, craft, availability and price filters; supported sorting; zero-result recovery.
- Product: real product-only galleries with zoom/swipe, required size selection, verified-only expandable details, add to bag, Buy Now to checkout preparation, contextual WhatsApp, custom-dyeing enquiry only when the stored customisation field explicitly supports dyeing, admin-approved Complete the Look, relevant recommendation groups and mobile sticky add.
- Product detail pages also include a genuine-image “A closer look” section, above-fold fabric/work/dispatch facts, clean breadcrumb URLs, dynamic titles/meta/canonical links and Product structured data.
- Shop and collection states publish dynamic titles, descriptions, canonical links and ItemList structured data; home publishes WebSite search structured data.
- Wishlist and cart: guest state persists in browser local storage; signed-in customer state persists to the account in Mongo. Cart drawer and full cart page include quantities and contextual WhatsApp order handoff.
- Customer account: email/password signup and login, profile editing, saved wishlist/cart continuity, prior order history, text invoice download and milestone tracking. A clearly labelled demo order exists only on the demo customer.
- Admin: hidden from storefront navigation, server-protected by the admin role, and available only after separate admin authentication. `/admin` is the overview; `/admin/products` manages complete product content, size-level inventory, URL/direct-upload image galleries, Complete the Look, merchandising and Draft/Active/Archived publishing; `/admin/collections` manages standalone customer-facing categories and collections with confirmed Archive/Restore actions and no destructive collection deletion; `/admin/homepage` edits hero, announcements, section headings, story, imagery and section visibility while retaining the fixed SAFYRA layout. Admins can also change passwords while verified or recover with the private security question and rate-limited answer check.
- Admin order management: protected `/admin/orders` lists/searches/filters unpaid requests, manages separately guarded payment and fulfilment states, shipping/tracking/internal notes, exceptional refund tracking, cancellation, duplicate-resistant conversion, manual WhatsApp previews and append-only internal history. Dependency-free print views create a clearly labelled order invoice with saved prices and a price-free packing slip using only stored order/customer values; missing tax, legal seller, statutory invoice and final shipping-charge fields are explicitly disclosed rather than invented.
- Customer waitlist: genuinely unavailable products offer a “Limited availability · Join the waitlist” modal. Name and mobile are required, email is optional, size is required only when the product has configured sizes, and colour is requested only when multiple configured colours exist. Single configured colours are recorded automatically; no size or variant is invented.
- Admin waitlist management: protected `/admin/waitlist` supports customer/product search, lifecycle filtering, detail review, internal notes and Waiting → Contacted → Converted / Closed status tracking.
- Checkout preparation: guest-friendly validated international address capture with searchable country/state/city suggestions, country-aware phone/postal validation, country-aligned shipping selection, cart-note persistence, saved unpaid order requests, review, completion guidance and contextual WhatsApp follow-up only after a request reference exists. Generic WhatsApp help remains separate. No payment processor is connected and no order is confirmed until payment is completed.
- Abandoned checkout recovery: checkout activity is upserted only after a valid name and email/mobile are entered, remains In progress for 30 minutes, becomes Abandoned after inactivity, and links to the resulting order request on completion. A protected `/admin/abandoned-checkouts` workspace exposes captured details, completion state, internal activity and recovery-email status.

## Data model
`Product`: id, title, slug, category, collection, fabric, craft, price, optional verified mrp, stock, stock_by_size, approved sizes/colours/images, optional verified description/specifications, origin, occasion/style search terms, size-guide image, availability, merchandising flags, Draft/Active/Archived status and admin-approved complete-look product IDs. Only Active (or legacy status-less) products are public.

`CatalogGroup`: id, name, slug, group_type (`category` or `collection`), description, image_url, Draft/Active/Archived status, sort_order and show_on_home. Product assignments remain string-based for compatibility with the existing catalogue.

`HomepageSettings`: one `homepage` document containing announcement messages, fixed-layout hero content, section visibility and headings, brand-story content/images and WhatsApp section copy. Customer pages always retain local SAFYRA defaults if the content API is unavailable.

`MediaUpload`: protected admin image uploads accept JPG, PNG and WebP up to 8 MB and return same-origin `/api/media/...` URLs. Existing Shopify CDN image URLs remain valid and unchanged.

`OrderRequest`: id, request_number, received_at, optional customer_id, validated contact/delivery fields, shipping selection, customer note, server-priced product items and subtotal. It represents an unpaid request, not a confirmed order.

`WaitlistRequest`: id, product snapshot, required customer name/mobile, optional normalized email, applicable configured size/colour, status, internal notes and timestamps. Active Waiting/Contacted requests are deduplicated for the same product and applicable variant when either normalized mobile or email matches. Converted/Closed requests release the active duplicate lock so the customer may join again later.

`CheckoutSession`: stable session key, checkout reference, captured contact/address snapshot, server-priced items, In progress/Abandoned/Completed status, linked order request, one-email reminder state and internal activity. Session-key upserts prevent duplicate checkouts while order linkage permanently suppresses recovery sends.

Stock enforcement: currently-unavailable products cannot be purchased; made-to-order products are not blocked by zero on-hand stock; other products use selected-size stock when present and otherwise global stock. The same rule is rechecked when an order request is submitted.
Published products that this existing rule determines to be genuinely unavailable display “YOU MISSED IT” on product cards and product detail pages, with purchase controls disabled. Made-to-order sizes remain selectable regardless of zero on-hand stock.
The waitlist API independently rechecks genuine unavailability and configured variants before accepting a request; available products, invalid sizes/colours and active duplicates are rejected server-side.

## Trust and accuracy
The public catalog contains only the four products captured from the approved prior SAFYRA data pull: Nazakat, Aira, Vaaya and Sang-e-Mar-Mar. Test/debug and unapproved placeholder products are removed. Product names, public prices, genuine compare-at prices, known fabrics, craft details and dispatch windows are grounded in the stored approved data. Empty or unverified fields are omitted. No percentage discounts, ratings, review quotes, customer counts, urgency timers or invented public stock claims are shown.

## Auth
Authentication uses a random opaque token in a secure, httpOnly, same-site cookie. Only the SHA-256 token digest is stored server-side; passwords and the admin recovery answer use salted PBKDF2-SHA256. Customer and administrator roles are enforced by backend dependencies, including every product mutation. Logout clears the server session and the full query cache.

## Integrations
Emergent-managed Resend sends at most one transactional abandoned-checkout reminder two hours after last activity. A platform cron checks every 15 minutes; the server claims each eligible session atomically, records provider acceptance/failure in Admin, never retries a failed attempt automatically, and never sends WhatsApp or marketing messages. The sender display name is SAFYRA CHIKANKARI and no Reply-To is configured.
No PayU or Shopify checkout code was changed in the editable-admin phase. Custom PayU Hosted Checkout remains blocked until SAFYRA supplies test credentials, confirms Hosted Checkout/test methods, and confirms the India shipping charge below ₹1,299; no manual payment-link fallback is permitted.
No courier-label API is integrated. Manual courier name, tracking number/link and shipping notes remain unchanged and must not be represented as a generated courier label.