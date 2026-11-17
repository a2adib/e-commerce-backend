import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_store_settings(client: AsyncClient, admin_auth, customer_auth):
    _, admin_headers = admin_auth
    _, customer_headers = customer_auth

    # 1. Public can read store settings
    res = await client.get("/settings")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "brand_name" in data

    # 2. Customer cannot update settings (403)
    res_cust = await client.put(
        "/settings",
        json={"brand_name": "Hacked Store"},
        headers=customer_headers,
    )
    assert res_cust.status_code == 403

    # 3. Admin can update store settings
    res_admin = await client.put(
        "/settings",
        json={"brand_name": "STREETWEAR CO", "logo_url": "https://example.com/logo.png"},
        headers=admin_headers,
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["data"]["brand_name"] == "STREETWEAR CO"


@pytest.mark.asyncio
async def test_coupons_and_checkout_discount(client: AsyncClient, admin_auth, customer_auth):
    _, admin_headers = admin_auth
    _, customer_headers = customer_auth

    # 1. Admin creates Category & Product
    cat_res = await client.post(
        "/admin/categories",
        json={"name": "Apparel", "slug": "apparel"},
        headers=admin_headers,
    )
    cat_pid = cat_res.json()["data"]["public_id"]

    prod_res = await client.post(
        "/admin/products",
        json={
            "name": "Hoodie",
            "slug": "street-hoodie",
            "price": 100.0,
            "stock_qty": 20,
            "images": ["https://example.com/hoodie.jpg"],
            "category_public_id": cat_pid,
        },
        headers=admin_headers,
    )
    prod_pid = prod_res.json()["data"]["public_id"]

    # 2. Admin creates a 20% coupon
    coupon_res = await client.post(
        "/admin/coupons",
        json={
            "code": "SAVE20",
            "discount_type": "percentage",
            "discount_value": 20.0,
            "min_order_amount": 50.0,
            "max_discount_amount": 50.0,
        },
        headers=admin_headers,
    )
    assert coupon_res.status_code == 201
    assert coupon_res.json()["data"]["code"] == "SAVE20"

    # 3. Customer validates coupon with subtotal 100 -> discount 20
    val_res = await client.post(
        "/coupons/validate",
        json={"code": "save20", "subtotal": 100.0},
    )
    assert val_res.status_code == 200
    val_data = val_res.json()["data"]
    assert val_data["valid"] is True
    assert val_data["discount_amount"] == 20.0
    assert val_data["new_subtotal"] == 80.0

    # 4. Customer adds product to cart and checks out with coupon
    await client.post(
        "/cart/items",
        json={"product_public_id": prod_pid, "quantity": 1},
        headers=customer_headers,
    )

    checkout_res = await client.post(
        "/checkout",
        json={
            "address": {
                "full_name": "John Doe",
                "phone": "+1234567890",
                "address_line": "123 Main St",
                "city": "Metropolis",
                "district": "Central",
            },
            "coupon_code": "SAVE20",
        },
        headers=customer_headers,
    )
    assert checkout_res.status_code == 201
    order_data = checkout_res.json()["data"]
    assert order_data["subtotal"] == 100.0
    assert order_data["discount"] == 20.0
    assert order_data["total"] == 130.0  # 100 - 20 + 50 delivery
    assert order_data["coupon_code"] == "SAVE20"

    # 5. Public Order Tracking
    track_res = await client.get(
        f"/orders/track?order_number={order_data['order_number']}&phone=1234567890"
    )
    assert track_res.status_code == 200
    assert track_res.json()["data"]["order_number"] == order_data["order_number"]


@pytest.mark.asyncio
async def test_product_reviews(client: AsyncClient, admin_auth, customer_auth):
    _, admin_headers = admin_auth
    _, customer_headers = customer_auth

    # 1. Admin creates Category & Product
    cat_res = await client.post(
        "/admin/categories",
        json={"name": "Accessories", "slug": "accessories"},
        headers=admin_headers,
    )
    cat_pid = cat_res.json()["data"]["public_id"]

    prod_res = await client.post(
        "/admin/products",
        json={
            "name": "Leather Cap",
            "slug": "leather-cap",
            "price": 35.0,
            "stock_qty": 10,
            "images": ["https://example.com/cap.jpg"],
            "category_public_id": cat_pid,
        },
        headers=admin_headers,
    )
    prod_pid = prod_res.json()["data"]["public_id"]

    # 2. Check initial reviews
    rev_res = await client.get(f"/products/{prod_pid}/reviews")
    assert rev_res.status_code == 200
    assert rev_res.json()["data"]["total_reviews"] == 0
    assert rev_res.json()["data"]["avg_rating"] == 0.0

    # 3. Customer posts a review
    post_rev = await client.post(
        f"/products/{prod_pid}/reviews",
        json={
            "rating": 5,
            "title": "Incredible Quality!",
            "comment": "Best leather cap I have ever owned. Fits perfectly.",
        },
        headers=customer_headers,
    )
    assert post_rev.status_code == 201
    assert post_rev.json()["data"]["rating"] == 5

    # 4. Check reviews summary again
    summary_res = await client.get(f"/products/{prod_pid}/reviews")
    assert summary_res.status_code == 200
    summary = summary_res.json()["data"]
    assert summary["total_reviews"] == 1
    assert summary["avg_rating"] == 5.0
    assert len(summary["reviews"]) == 1
    assert summary["reviews"][0]["title"] == "Incredible Quality!"
