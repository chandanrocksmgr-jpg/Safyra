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
- Admin: hidden from storefront navigation, server-protected by the admin role, and available only after separate admin authentication. Admins can add/edit/delete products, change passwords while verified, or recover with the private security question and rate-limited answer check.
- Admin order management: protected `/admin/orders` lists/searches/filters unpaid requests, manages separately guarded payment and fulfilment states, shipping/tracking/internal notes, exceptional refund tracking, cancellation, duplicate-resistant conversion, manual WhatsApp previews and append-only internal history.
- Checkout preparation: guest-friendly validated international address capture with searchable country/state/city suggestions, country-aware phone/postal validation, country-aligned shipping selection, cart-note persistence, saved unpaid order requests, review, completion guidance and contextual WhatsApp follow-up only after a request reference exists. Generic WhatsApp help remains separate. No payment processor is connected and no order is confirmed until payment is completed.

## Data model
`Product`: id, title, slug, category, collection, fabric, craft, price, optional verified mrp, stock, stock_by_size, approved sizes/colours/images, optional verified description/specifications, origin, occasion/style search terms, size-guide image, availability, merchandising flags and admin-approved complete-look product IDs.

`OrderRequest`: id, request_number, received_at, optional customer_id, validated contact/delivery fields, shipping selection, customer note, server-priced product items and subtotal. It represents an unpaid request, not a confirmed order.

Stock enforcement: currently-unavailable products cannot be purchased; made-to-order products are not blocked by zero on-hand stock; other products use selected-size stock when present and otherwise global stock. The same rule is rechecked when an order request is submitted.

## Trust and accuracy
The public catalog contains only the four products captured from the approved prior SAFYRA data pull: Nazakat, Aira, Vaaya and Sang-e-Mar-Mar. Test/debug and unapproved placeholder products are removed. Product names, public prices, genuine compare-at prices, known fabrics, craft details and dispatch windows are grounded in the stored approved data. Empty or unverified fields are omitted. No percentage discounts, ratings, review quotes, customer counts, urgency timers or invented public stock claims are shown.

## Auth
Authentication uses a random opaque token in a secure, httpOnly, same-site cookie. Only the SHA-256 token digest is stored server-side; passwords and the admin recovery answer use salted PBKDF2-SHA256. Customer and administrator roles are enforced by backend dependencies, including every product mutation. Logout clears the server session and the full query cache.