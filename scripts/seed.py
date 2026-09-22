import asyncio
import os
import sys

# Ensure root project directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import async_session_factory
import src.models  # Ensures all SQLModel relationships are loaded into registry
from src.auth.models import User, UserRole
from src.auth.services import hash_password
from src.categories.models import Category
from src.products.models import Product
from src.home.models import HomePage, HomePageStatus
from src.config import settings
from sqlalchemy.orm import configure_mappers
from sqlmodel import select

# Ensure all SQLAlchemy relationships and foreign keys are resolved
configure_mappers()


async def seed():
    print("🌱 Starting database seeding...")
    async with async_session_factory() as session:
        # 1. Seed Admin User
        admin_email = "admin@ecommerce.com"
        admin_res = await session.exec(select(User).where(User.email == admin_email))
        admin = admin_res.first()
        if not admin:
            admin = User(
                name="Store Administrator",
                email=admin_email,
                phone="+8801700000000",
                password_hash=hash_password("AdminPass123!"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(admin)
            print(f"✅ Admin created: {admin_email} / AdminPass123!")
        else:
            print(f"ℹ️ Admin already exists: {admin_email}")

        # Seed Sample Customer
        cust_email = "customer@ecommerce.com"
        cust_res = await session.exec(select(User).where(User.email == cust_email))
        customer = cust_res.first()
        if not customer:
            customer = User(
                name="John Doe",
                email=cust_email,
                phone="+8801800000000",
                password_hash=hash_password("CustomerPass123!"),
                role=UserRole.CUSTOMER,
                is_active=True,
            )
            session.add(customer)
            print(f"✅ Customer created: {cust_email} / CustomerPass123!")

        # 2. Seed Categories
        categories_data = [
            {"name": "Electronics", "slug": "electronics", "description": "Gadgets, smartphones, and computers"},
            {"name": "Apparel & Fashion", "slug": "fashion", "description": "Men and women clothing and accessories"},
            {"name": "Home & Kitchen", "slug": "home-kitchen", "description": "Cookware, decor, and furniture"},
        ]
        created_categories = {}
        for cdata in categories_data:
            c_res = await session.exec(select(Category).where(Category.slug == cdata["slug"]))
            cat = c_res.first()
            if not cat:
                cat = Category(**cdata, is_active=True)
                session.add(cat)
                await session.flush()
                print(f"✅ Category created: {cat.name}")
            created_categories[cdata["slug"]] = cat

        # 3. Seed Products
        products_data = [
            {
                "name": "Wireless Noise Cancelling Headphones",
                "slug": "wireless-headphones",
                "description": "High fidelity audio with 30-hour battery life and fast charging.",
                "price": 199.99,
                "compare_at_price": 249.99,
                "sku": "ELEC-HD-001",
                "stock_qty": 50,
                "images": ["https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800"],
                "is_featured": True,
                "category_id": created_categories["electronics"].id,
            },
            {
                "name": "Smart Fitness Watch",
                "slug": "smart-fitness-watch",
                "description": "Track health, heart rate, sleep quality, and workouts with AMOLED display.",
                "price": 89.99,
                "compare_at_price": 120.00,
                "sku": "ELEC-SW-002",
                "stock_qty": 35,
                "images": ["https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800"],
                "is_featured": True,
                "category_id": created_categories["electronics"].id,
            },
            {
                "name": "Classic Cotton Crewneck T-Shirt",
                "slug": "classic-cotton-tshirt",
                "description": "Premium 100% organic cotton t-shirt with modern breathable fit.",
                "price": 24.99,
                "compare_at_price": 35.00,
                "sku": "FASH-TS-003",
                "stock_qty": 120,
                "images": ["https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=800"],
                "is_featured": False,
                "category_id": created_categories["fashion"].id,
            },
            {
                "name": "Stainless Steel Pour-Over Kettle",
                "slug": "pour-over-kettle",
                "description": "Gooseneck spout for precision temperature and water flow brewing.",
                "price": 49.50,
                "compare_at_price": 60.00,
                "sku": "HOME-KT-004",
                "stock_qty": 20,
                "images": ["https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=800"],
                "is_featured": True,
                "category_id": created_categories["home-kitchen"].id,
            },
        ]
        for pdata in products_data:
            p_res = await session.exec(select(Product).where(Product.slug == pdata["slug"]))
            p = p_res.first()
            if not p:
                p = Product(**pdata, is_active=True)
                session.add(p)
                print(f"✅ Product created: {p.name}")

        # 4. Seed Default Published Home Page
        hp_res = await session.exec(select(HomePage).where(HomePage.status == HomePageStatus.PUBLISHED))
        hp = hp_res.first()
        if not hp:
            hp = HomePage(
                status=HomePageStatus.PUBLISHED,
                sections=[
                    {
                        "id": "sec_hero_1",
                        "type": "hero_banner",
                        "is_visible": True,
                        "config": {
                            "autoplay": True,
                            "interval_seconds": 5,
                            "slides": [
                                {
                                    "image_url": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1200",
                                    "title": "Welcome to Modern Commerce",
                                    "subtitle": "Discover curated gear, tech, and everyday essentials.",
                                    "cta_text": "Explore Products",
                                    "cta_link": "/products",
                                								},
                            ],
                        },
                    },
                    {
                        "id": "sec_cat_2",
                        "type": "category_grid",
                        "is_visible": True,
                        "config": {
                            "title": "Browse Popular Categories",
                            "columns": 3,
                            "category_slugs": ["electronics", "fashion", "home-kitchen"],
                        },
                    },
                    {
                        "id": "sec_feat_3",
                        "type": "featured_products",
                        "is_visible": True,
                        "config": {
                            "title": "Trending Now",
                            "limit": 6,
                        },
                    },
                ],
            )
            session.add(hp)
            print("✅ Default published home page created.")

        await session.commit()
        print("🌱 Seeding finished successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
