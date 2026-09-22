# E-Commerce Platform REST API

A production-ready asynchronous REST API for an e-commerce platform that powers two distinct frontends: an **Admin Panel** and a **Customer Storefront**.

Built with **Python 3.12+**, **FastAPI (async)**, **SQLModel + async SQLAlchemy**, **PostgreSQL**, **Alembic**, **Redis** (caching & rate limiting), and **Celery** (asynchronous background workers).

---

## 🏗 System Architecture & Key Design Decisions

1. **Layered Architecture**:
   - `routers/`: Endpoint definitions, parameter parsing, and dependency injection only. **No business logic**.
   - `services/`: Encapsulates all domain workflows, stock checks, atomic transactions, and business invariants.
   - `models/` & `schemas/`: SQLModel table declarations and Pydantic v2 validation / serialization schemas.
   - `common/`: Shared mixins (`CommonFieldMixin` with integer PK + 11-character `public_id`, auto timestamps, and soft-delete `is_active`), unified response envelopes, and centralized error handling.

2. **Strict RBAC & Tenant Isolation**:
   - Built-in roles: `admin` and `customer`.
   - Admin routes (`/admin/*`) strictly require `admin` privileges.
   - Customer routes enforce that customers can only read/mutate their own cart, orders, wishlist, and addresses (`customer_id` resolved directly from JWT).
   - Strict API separation for registration: public registration only creates `customer` users. Admin creation is secured via `ADMIN_SETUP_KEY` or existing admin authorization.

3. **External vs. Internal Identifiers**:
   - Internal integer auto-incrementing `id` is strictly used for high-performance foreign keys and joins.
   - External APIs exclusively expose and accept random, url-safe, 11-character `public_id`s (e.g., `xK9L1Jt8QmP`).

4. **Atomic Checkout & Finite State Machine (FSM)**:
   - Checkout runs inside a single database transaction: validates product availability and inventory, deducts stock, snapshots pricing, records shipping details, generates a human-readable order number (`ORD-YYYYMMDD-XXXX`), logs initial status history, and clears the user's cart.
   - Order lifecycle strictly transitions through an FSM (`pending` → `confirmed` → `processing` → `shipped` → `delivered` or `cancelled`).
   - Cancelling an order restores inventory back to the active catalog atomically.
   - Every status modification records an immutable entry into `OrderStatusHistory`.

5. **Dynamic Home Page Section Builder**:
   - Flexible JSON-based section composer supporting `hero_banner`, `category_grid`, `product_carousel`, `promo_banner`, `rich_text`, and `featured_products`.
   - Validated at the API boundary via Pydantic discriminated unions.
   - Published home configuration is cached in Redis with high TTL and automatically invalidated on draft publish.

6. **Celery Worker & Redis**:
   - Order confirmation notifications dispatched asynchronously via Celery (`send_order_confirmation_email`).
   - In-memory fallback and eager execution mode for unit tests.

---

## 🚀 Quick Start (Local Docker Compose)

The easiest way to run the complete environment (PostgreSQL, Redis, FastAPI App, and Celery Worker):

```bash
# 1. Clone the repository and navigate to root
cd e_commerce_backend

# 2. Copy the sample environment file
cp .env.example .env

# 3. Build and launch all services with Docker Compose
docker compose up --build
```

The services will start on:
- **FastAPI API & Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`
- **Celery Worker**: running in background processing queue `ecommerce_tasks`

---

## 🛠 Manual Local Development Setup

### 1. Prerequisites
- Python 3.12+
- PostgreSQL
- Redis

### 2. Setup Virtual Environment & Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables
Create `.env` from `.env.example`:
```bash
cp .env.example .env
```
Ensure your `DATABASE_URL` and `REDIS_URL` are accessible.

### 4. Database Migrations
Run Alembic migrations to create tables:
```bash
alembic upgrade head
```

### 5. Seed Initial Data
Populates default admin user, test customer, categories, products, and default home page:
```bash
python -m scripts.seed
```

**Default Credentials created by seed:**
- **Admin**: `admin@ecommerce.com` / `AdminPass123!`
- **Customer**: `customer@ecommerce.com` / `CustomerPass123!`

### 6. Run the API Server
```bash
uvicorn src.main:app --reload --port 8000
```

### 7. Run Celery Worker (Optional in separate terminal)
```bash
celery -A src.orders.tasks.celery_app worker --loglevel=info
```

---

## 🧪 Running Tests

A comprehensive asynchronous test suite built with `pytest` and `httpx` verifies authentication, RBAC, customer cart/wishlist/address workflows, checkout transactions, inventory deduction, order state transitions, and home builder publishing.

```bash
source .venv/bin/activate
pytest -v
```

Tests run in an isolated in-memory SQLite database with eager Celery execution mode and mock Redis resilience, completing in ~1 second.

---

## 📖 API Documentation Summary

Interactive OpenAPI (Swagger) documentation is available at `/docs` and ReDoc at `/redoc`.

### 🔐 Authentication (`/auth`)
| Method | Path | Description | Access |
|---|---|---|---|
| `POST` | `/auth/register` | Register a new customer | Public |
| `POST` | `/auth/login` | Login with email & password (returns access + refresh tokens) | Public |
| `POST` | `/auth/refresh` | Rotate refresh token & get new access token | Public |
| `POST` | `/auth/logout` | Revoke refresh token | Authenticated |
| `GET` | `/auth/me` | Current authenticated user profile | Authenticated |
| `POST` | `/auth/admin/register` | Create an admin account | Secure Key / Admin |

### 🛍 Storefront Endpoints (`/products`, `/categories`, `/cart`, `/wishlist`, `/orders`, `/home`)
| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/categories` | List active category tree | Public |
| `GET` | `/products` | List active products with search, filtering & pagination | Public |
| `GET` | `/products/{slug}` | Get single active product by slug | Public |
| `GET` | `/cart` | Get customer cart with live pricing and stock validation | Customer |
| `POST` | `/cart/items` | Add product to cart | Customer |
| `PATCH` | `/cart/items/{id}` | Update quantity of item in cart | Customer |
| `DELETE` | `/cart/items/{id}` | Remove item from cart | Customer |
| `DELETE` | `/cart` | Clear cart | Customer |
| `GET` | `/wishlist` | Get customer wishlist items | Customer |
| `POST` | `/wishlist/{product_id}` | Add product to wishlist | Customer |
| `DELETE` | `/wishlist/{product_id}` | Remove product from wishlist | Customer |
| `GET` | `/addresses` | List customer shipping addresses | Customer |
| `POST` | `/addresses` | Add new shipping address | Customer |
| `POST` | `/checkout` | Perform atomic checkout from cart | Customer |
| `GET` | `/orders/me` | List own orders | Customer |
| `GET` | `/orders/me/{id}` | Get own order details & status history | Customer |
| `POST` | `/orders/me/{id}` | Cancel own pending order (restores stock) | Customer |
| `GET` | `/home` | Fetch cached published home page sections | Public |

### ⚙️ Admin Endpoints (`/admin/*`)
| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/admin/dashboard` | Dashboard metrics: total revenue, order counts, low stock alerts | Admin |
| `GET/POST` | `/admin/categories` | Manage all categories (including inactive) | Admin |
| `PATCH/DELETE`| `/admin/categories/{id}` | Edit or toggle active status of category | Admin |
| `GET/POST` | `/admin/products` | Manage all products with stock and image uploads | Admin |
| `PATCH/DELETE`| `/admin/products/{id}` | Edit product details or toggle active status | Admin |
| `POST` | `/admin/products/{id}/images` | Upload product images | Admin |
| `GET` | `/admin/orders` | List and search all orders with rich filters | Admin |
| `POST` | `/admin/orders` | Create manual order on behalf of customer | Admin |
| `PATCH` | `/admin/orders/{id}/status` | Transition order status (validates FSM transitions) | Admin |
| `GET/POST` | `/admin/home` | Get/save draft home page section configurations | Admin |
| `POST` | `/admin/home/publish` | Publish home page draft to storefront & clear Redis cache | Admin |
| `GET` | `/admin/users` | List customer accounts with order counts and spend | Admin |
