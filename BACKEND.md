# KalaKatte: backend hookup guide

Project: artisan marketplace for coastal Karnataka crafts (Kasuti, Beedu, etc.), DevHack 2026 PS 4.2.
Status: **UI only**. Data is mocked in the browser. No auth yet (owner will add it later).

## Files
- `index.html`: the whole frontend (HTML + CSS + JS, no build step).

You do **not** need to read the whole file. Only touch these marked sections in `index.html`:

| Section marker (search for it) | What it is |
|---|---|
| `CONFIG` | `USE_MOCK`, `API_BASE`, `LABOUR_RATE` |
| `API LAYER` | `API` object: every data call goes through here |
| `I18N` | translation dictionary `T` (kn, tcy, en) |

Views, router and events don't talk to data directly, only through `API.*`.

## Switch to the real backend
1. In `CONFIG`: set `USE_MOCK: false` and `API_BASE` to the server URL (empty string if served from the same origin).
2. Implement the endpoints below. The `API` object already calls them.
3. If frontend and backend are on different origins, enable CORS on the backend.

## Endpoint contract

| Function | Method + path | Request body | Response |
|---|---|---|---|
| `API.listProducts()` | `GET /api/products` | none | `Product[]` (newest first) |
| `API.getProduct(id)` | `GET /api/products/:id` | none | `Product` (404 if missing) |
| `API.createProduct(d)` | `POST /api/products` | `Product` without `id` | created `Product` |
| `API.createOrder(d)` | `POST /api/orders` | `Order` without `id`, `status`, `created_at` | created `Order` |
| `API.listOrders()` | `GET /api/orders` | none | `Order[]` (newest first) |
| `API.setOrderStatus(id, status)` | `PATCH /api/orders/:id` | `{ "status": "shipped" }` | updated `Order` |

### Product
```json
{
  "id": "p1",
  "craft": "kasuti",            // kasuti | beedu | wood | other
  "price": 850,                 // INR, number
  "hours": 10,
  "materials_cost": 200,
  "image_url": "/uploads/x.jpg", // optional, UI draws a placeholder if missing
  "name": "", "artisan_name": "", "village": "", "materials": "", "story": "",
  "name_kn": "", "name_en": ""   // optional localised variants (see below)
}
```
Localised fields: for each of `name`, `artisan_name`, `village`, `materials`, `story`, the UI reads `<field>_kn` / `<field>_en` and falls back to the plain `<field>`. Products created through the Sell form only send the plain fields, so the backend can store just those. Seed data in `SEED` shows both styles.

### Order
```json
{
  "id": "KK123456",
  "items": [{ "product_id": "p1", "name": "…", "price": 850, "qty": 2 }],
  "total": 1700,
  "buyer_name": "", "phone": "", "address": "",
  "payment_method": "demo",      // demo | cod
  "status": "paid",              // placed | paid | shipped
  "created_at": "ISO string"
}
```
Payment is **mocked on purpose** (rulebook allows it). Rule used in the mock: `demo` becomes `paid`, `cod` becomes `placed`. Replicate this in the backend `POST /api/orders`.

## Known gaps to wire up
- **Image upload**: the Sell form currently stores the photo as a base64 data URL (`#photo` change handler in EVENTS). Replace with an upload (e.g. `POST /api/upload` returning a URL), then put that URL in `image_url`.
- **Auth**: none. When added, send the token in the `http()` helper headers. "My orders" and "Sell" should then be filtered or guarded per user (`GET /api/orders` currently returns all orders; artisan vs buyer split is not modelled).
- **Order status**: "Mark as shipped" button is visible to everyone for now. Restrict to the artisan once auth exists.
- **Not built yet**: QR code per product linking to its story page (route `#/p/:id` already exists), voice-based listing, real payments.

## i18n
- Languages: `kn` (default), `tcy` (Tulu, written in Kannada script), `en`. Choice is saved in `localStorage` key `kk_lang`.
- Add or edit text in the `T` object. A missing `tcy` key falls back to `kn`, then to the key name.
- **Tulu strings are a small set and should be reviewed by a native speaker**; everything else intentionally falls back to Kannada.

## Local mock data
Mock mode stores products, orders, cart in `localStorage` (keys `kk_products`, `kk_orders`, `kk_cart`). Clear them to reset the demo.

## Deploy notes (Oracle, planned)
- Serve `index.html` as a static file from the same server as the API to avoid CORS.
- Instance is small (1 GB RAM): prefer Flask/FastAPI or Express + SQLite, no Docker, run behind gunicorn or pm2.
- Open ports 80/443 in both the Oracle security list and the instance firewall.
- Frontend loads Noto Sans fonts from Google Fonts. For offline use, self-host them.
