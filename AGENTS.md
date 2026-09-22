# Database Schema & Stack Summary

## Infrastructure
- **Database**: Vercel Postgres
- **Image Storage**: Vercel Blob
- **Auth**: Firebase (Google Auth)

## Mixin Chain (`src/common/mixins.py`)
`CommonFieldMixin` → `IDMixin` → `TimestampMixin` → `SQLModel`
- `id`: int (Auto-inc PK, internal FK)
- `public_id`: str (11-char uniq idx, external API)
- `created_at`/`updated_at`: datetime (UTC, auto-managed)
- `is_active`: bool (Soft delete, def: `True`)

## Tables

### users
- `email` (str, uniq idx), `password_hash` (str, bcrypt), `full_name` (str)
- `role` (enum: `admin`|`customer`, def: `customer`)
- `google_id` (str?, uniq idx, via Firebase)
- `avatar_url` (str?, via `media_assets`)
- **rels**: `orders` (1:M), `uploads` (1:M, `media_assets`)

### media_assets
- `filename` (str), `url` (str, Vercel Blob, uniq idx)
- `mime_type` (str), `size_bytes` (int)
- `uploaded_by` (int?, FK `users.id`)
- **rels**: `uploader` (M:1)

### categories
- `name` (str), `slug` (str, uniq idx), `description` (str?)
- `image_url` (str?, via `media_assets`)
- `parent_id` (int?, FK `categories.id`)
- **rels**: `parent` (M:1), `children` (1:M), `products` (1:M)

### products
- `name` (str), `slug` (str, uniq idx), `description` (str?)
- `price` (float, `>=0`), `stock_quantity` (int, `>=0`)
- `image_urls` (list[str], JSON, via `media_assets`)
- `is_featured` (bool, def: `False`)
- `category_id` (int, FK `categories.id`)
- **rels**: `category` (M:1), `order_items` (1:M)

### orders
- `user_id` (int, FK `users.id`)
- `status` (enum: `pending`→`confirmed`→`processing`→`shipped`→`delivered` | `cancelled`)
- `total_amount` (float, `>=0`)
- `stripe_payment_intent_id` (str?, uniq idx, webhook-set)
- `tracking_number` (str?), `shipping_address` (JSON)
- **rels**: `user` (M:1), `items` (1:M)

### order_items
- `order_id` (int, FK `orders.id`), `product_id` (int, FK `products.id`)
- `quantity` (int, `>=1`), `unit_price` (float, `>=0`, order-time snapshot)
- **rels**: `order` (M:1), `product` (M:1)

## Architecture Rules
1. **FK Convention**: Use internal integer `id` for joins. APIs accept/return `public_id`. Service layer handles `public_id` → `id` resolution before DB operations.
2. **Soft Delete**: All tables use `is_active=False`. Service layer queries must filter `is_active=True`. Application handles cascade checks.
3. **Media Handler System**: Centralized asset management.
   - *Upload*: Stream new files to Vercel Blob, save metadata/URL to `media_assets`, return URL.
   - *Reuse*: Query `media_assets` gallery to select and attach existing URLs to entities (Products/Categories/Avatars) without re-uploading.
4. **User Creation APIs**: Strict separation by role.
   - *Customer Registration*: Public endpoint that only creates users with the `customer` role.
   - *Admin Creation*: Separate, secured endpoint dedicated to creating users with the `admin` role (should require existing admin privileges or a secure setup key).
