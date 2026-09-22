import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.common.exceptions import APIError, api_error_handler, http_exception_handler
from src.common.redis import close_redis_client
import src.models  # Guarantees all model relationships are loaded into SQLAlchemy mapper registry

# Routers
from src.auth.routes import router as auth_router
from src.products.routes import public_router as products_public_router, admin_router as products_admin_router
from src.categories.routes import public_router as categories_public_router, admin_router as categories_admin_router
from src.cart.routes import router as cart_router
from src.wishlist.routes import router as wishlist_router
from src.addresses.routes import router as addresses_router
from src.orders.routes import customer_router as orders_customer_router, admin_router as orders_admin_router
from src.admin.routes import router as admin_core_router
from src.home.routes import public_router as home_public_router, admin_router as home_admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure storage uploads directory exists
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    yield
    # Teardown Redis connections
    await close_redis_client()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "auth", "description": "Authentication, registration, tokens, and password management"},
        {"name": "storefront", "description": "Public storefront browsing (products, categories, home)"},
        {"name": "customer", "description": "Customer personal account actions (cart, wishlist, addresses, orders)"},
        {"name": "admin", "description": "Admin panel management routes"},
        {"name": "health", "description": "Health check endpoints"},
    ],
)

# Exception handlers for consistent error schema: {"detail": ..., "code": ...}
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# Configure CORS for separate Customer (e.g. Next.js) and Admin (e.g. React) panels
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for local image uploads
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.STORAGE_DIR), name="uploads")

# Include Routers
app.include_router(auth_router)
app.include_router(products_public_router)
app.include_router(products_admin_router)
app.include_router(categories_public_router)
app.include_router(categories_admin_router)
app.include_router(cart_router)
app.include_router(wishlist_router)
app.include_router(addresses_router)
app.include_router(orders_customer_router)
app.include_router(orders_admin_router)
app.include_router(admin_core_router)
app.include_router(home_public_router)
app.include_router(home_admin_router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "debug_mode": settings.DEBUG}