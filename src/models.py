"""
Central models module to import all SQLModel tables in one place.
Ensures SQLAlchemy/SQLModel relationship registries resolve properly without KeyError.
"""
from src.common.mixins import TimestampMixin, IDMixin, CommonFieldMixin
from src.auth.models import User, UserRole
from src.categories.models import Category
from src.products.models import Product
from src.cart.models import Cart, CartItem
from src.wishlist.models import WishlistItem
from src.addresses.models import Address
from src.orders.models import Order, OrderItem, OrderStatusHistory
from src.home.models import HomePage

__all__ = [
    "TimestampMixin",
    "IDMixin",
    "CommonFieldMixin",
    "User",
    "UserRole",
    "Category",
    "Product",
    "Cart",
    "CartItem",
    "WishlistItem",
    "Address",
    "Order",
    "OrderItem",
    "OrderStatusHistory",
    "HomePage",
]
