# SAFYRA CHIKANKARI — Living Spec

## Purpose
Premium, mobile-first editorial ecommerce experience for handcrafted Lucknowi Chikankari. The build is independent of Shopify and uses a Mongo-backed demo catalog that SAFYRA staff can maintain through `/admin`.

## Core flows
- Home: editorial hero, category discovery, new arrivals, best sellers, SAFYRA Luxury, fabrics, extended sizes, craft story, honest customer-care statement, Instagram journal, founder philosophy.
- Shop: search, category/fabric filters, sorting, wishlist toggles, quick add.
- Product: gallery, size/color selection, size guide, complete specifications, add to bag, buy now, WhatsApp context, recommendations, collection/fabric links, mobile sticky add.
- Wishlist and cart: guest state persists in browser local storage; signed-in customer state persists to the account in Mongo. Cart drawer and full cart page include quantities and contextual WhatsApp order handoff.
- Customer account: email/password signup and login, profile editing, saved wishlist/cart continuity, prior order history, text invoice download and milestone tracking. A clearly labelled demo order exists only on the demo customer.
- Admin: hidden from storefront navigation, server-protected by the admin role, and available only after separate admin authentication. Admins can add/edit/delete products, change passwords while verified, or recover with the private security question and rate-limited answer check.

## Data model
`Product`: id, title, slug, category, collection, fabric, craft, price, mrp, stock, stock_by_size, sizes, colors, images, description, fit, measurements, transparency, lining, care, dispatch_days, availability, tags and merchandising flags.

## Trust and accuracy
Product names, public prices, core descriptions, known fabrics, craft details and dispatch windows for Nazakat, Aira, Vaaya and Sang-e-Mar-Mar are grounded in safyra.co. No ratings, review quotes, customer counts, urgency timers or exact public stock claims are shown.

## Auth
Authentication uses a random opaque token in a secure, httpOnly, same-site cookie. Only the SHA-256 token digest is stored server-side; passwords and the admin recovery answer use salted PBKDF2-SHA256. Customer and administrator roles are enforced by backend dependencies, including every product mutation. Logout clears the server session and the full query cache.