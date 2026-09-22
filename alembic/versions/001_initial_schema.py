"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-21 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('public_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column('password_hash', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('role', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('avatar_url', sqlmodel.sql.sqltypes.AutoString(length=512), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_public_id'), 'users', ['public_id'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Categories
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('public_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(length=1024), nullable=True),
        sa.Column('image_url', sqlmodel.sql.sqltypes.AutoString(length=512), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['categories.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categories_public_id'), 'categories', ['public_id'], unique=True)
    op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=True)

    # Products
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('public_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(length=4096), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('compare_at_price', sa.Float(), nullable=True),
        sa.Column('sku', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column('stock_qty', sa.Integer(), nullable=False, default=0),
        sa.Column('images', sa.JSON(), nullable=False),
        sa.Column('is_featured', sa.Boolean(), nullable=False, default=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_public_id'), 'products', ['public_id'], unique=True)
    op.create_index(op.f('ix_products_slug'), 'products', ['slug'], unique=True)
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=False)

    # Carts
    op.create_table(
        'carts',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('public_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_carts_public_id'), 'carts', ['public_id'], unique=True)
    op.create_index(op.f('ix_carts_user_id'), 'carts', ['user_id'], unique=True)

    # Cart Items
    op.create_table(
        'cart_items',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('public_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('cart_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['cart_id'], ['carts.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cart_id', 'product_id', name='uq_cart_product')
    )
    op.create_index(op.f('ix_cart_items_public_id'), 'cart_items', ['public_id'], unique=True)

    # Wishlist Items
    op.create_table(
        'wishlist_items',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('public_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_user_wishlist_product')
    )
    op.create_index(op.f('ix_wishlist_items_public_id'), 'wishlist_items', ['public_id'], unique=True)

    # Addresses
    op.create_table(
        'addresses',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('public_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('full_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('address_line', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column('city', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('district', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('postal_code', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_addresses_public_id'), 'addresses', ['public_id'], unique=True)
    op.create_index(op.f('ix_addresses_user_id'), 'addresses', ['user_id'], unique=False)

    # Orders
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('public_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('order_number', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('payment_method', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('payment_status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('subtotal', sa.Float(), nullable=False, default=0.0),
        sa.Column('delivery_charge', sa.Float(), nullable=False, default=0.0),
        sa.Column('discount', sa.Float(), nullable=False, default=0.0),
        sa.Column('total', sa.Float(), nullable=False, default=0.0),
        sa.Column('shipping_snapshot', sa.JSON(), nullable=False),
        sa.Column('note', sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_public_id'), 'orders', ['public_id'], unique=True)
    op.create_index(op.f('ix_orders_order_number'), 'orders', ['order_number'], unique=True)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)
    op.create_index(op.f('ix_orders_created_at'), 'orders', ['created_at'], unique=False)

    # Order Items
    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('public_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('product_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, default=1),
        sa.Column('line_total', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_items_public_id'), 'order_items', ['public_id'], unique=True)

    # Order Status History
    op.create_table(
        'order_status_history',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('public_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('from_status', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('to_status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('changed_by', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column('note', sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_status_history_public_id'), 'order_status_history', ['public_id'], unique=True)
    op.create_index(op.f('ix_order_status_history_order_id'), 'order_status_history', ['order_id'], unique=False)

    # Home Pages
    op.create_table(
        'home_pages',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('public_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('sections', sa.JSON(), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_home_pages_public_id'), 'home_pages', ['public_id'], unique=True)
    op.create_index(op.f('ix_home_pages_status'), 'home_pages', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('home_pages')
    op.drop_table('order_status_history')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('addresses')
    op.drop_table('wishlist_items')
    op.drop_table('cart_items')
    op.drop_table('carts')
    op.drop_table('products')
    op.drop_table('categories')
    op.drop_table('users')
