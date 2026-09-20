# SAFYRA CHIKANKARI — Living Spec

## Purpose
Premium, mobile-first editorial ecommerce experience for handcrafted Lucknowi Chikankari. The build is independent of Shopify and uses a Mongo-backed demo catalog that SAFYRA staff can maintain through `/admin`.

## Core flows
- Home: editorial hero, category discovery, new arrivals, best sellers, SAFYRA Luxury, fabrics, extended sizes, craft story, honest customer-care statement, Instagram journal, founder philosophy.
- Shop: search, category/fabric filters, sorting, wishlist toggles, quick add.
- Product: gallery, size/color selection, size guide, complete specifications, add to bag, buy now, WhatsApp context, recommendations, collection/fabric links, mobile sticky add.
- Wishlist and cart: persisted in browser local storage; cart drawer and full cart page include quantities and contextual WhatsApp order handoff.
- Admin: add, edit and delete products with title, category, collection, fabric, craft, price, stock, sizes, colors, imagery, description, fit, measurements, transparency, lining, care and dispatch time.

## Data model
`Product`: id, title, slug, category, collection, fabric, craft, price, mrp, stock, stock_by_size, sizes, colors, images, description, fit, measurements, transparency, lining, care, dispatch_days, availability, tags and merchandising flags.

## Trust and accuracy
Product names, public prices, core descriptions, known fabrics, craft details and dispatch windows for Nazakat, Aira, Vaaya and Sang-e-Mar-Mar are grounded in safyra.co. No ratings, review quotes, customer counts, urgency timers or exact public stock claims are shown.

## Auth
No authentication or role gating is included in this frontend-first build. The admin catalog is intentionally open for demonstration.