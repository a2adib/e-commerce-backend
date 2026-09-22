import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_checkout_transaction_and_stock_flow(client: AsyncClient, customer_auth, admin_auth):
    cust_user, cust_headers = customer_auth
    admin_user, admin_headers = admin_auth

    # 1. Admin creates product with stock 5
    cat = (await client.post(
        "/admin/categories",
        json={"name": "Kitchen", "slug": "kitchen"},
        headers=admin_headers,
    )).json()["data"]

    prod = (await client.post(
        "/admin/products",
        json={
            "name": "Coffee Maker",
            "slug": "coffee-maker",
            "price": 100.0,
            "stock_qty": 5,
            "category_public_id": cat["public_id"],
        },
        headers=admin_headers,
    )).json()["data"]

    # 2. Customer adds 2 items to cart
    await client.post(
        "/cart/items",
        json={"product_public_id": prod["public_id"], "quantity": 2},
        headers=cust_headers,
    )

    # 3. Checkout without phone / address fails with 422
    fail_res = await client.post(
        "/checkout",
        json={},
        headers=cust_headers,
    )
    assert fail_res.status_code == 422

    # 4. Valid Checkout transaction
    checkout_res = await client.post(
        "/checkout",
        json={
            "phone": "+8801700112233",
            "address": {
                "full_name": "Alice Customer",
                "phone": "+8801700112233",
                "address_line": "456 Market St",
                "city": "Dhaka",
                "district": "Dhaka",
                "postal_code": "1200",
            },
            "note": "Please deliver before 5pm",
        },
        headers=cust_headers,
    )
    assert checkout_res.status_code == 201
    order_data = checkout_res.json()["data"]
    order_pid = order_data["public_id"]
    assert order_data["status"] == "pending"
    assert order_data["subtotal"] == 200.0
    assert len(order_data["status_history"]) >= 1

    # Cart is now cleared
    cart_after = await client.get("/cart", headers=cust_headers)
    assert len(cart_after.json()["data"]["items"]) == 0

    # Product stock was decremented from 5 to 3
    prod_check = await client.get(f"/admin/products/{prod['public_id']}", headers=admin_headers)
    assert prod_check.json()["data"]["stock_qty"] == 3

    # 5. Customer cancels order while pending -> stock is restored from 3 to 5
    cancel_res = await client.post(
        f"/orders/me/{order_pid}/cancel",
        headers=cust_headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "cancelled"

    prod_restored = await client.get(f"/admin/products/{prod['public_id']}", headers=admin_headers)
    assert prod_restored.json()["data"]["stock_qty"] == 5


@pytest.mark.asyncio
async def test_order_status_transitions_and_history(client: AsyncClient, customer_auth, admin_auth):
    cust_user, cust_headers = customer_auth
    admin_user, admin_headers = admin_auth

    # Setup Product
    cat = (await client.post(
        "/admin/categories",
        json={"name": "Gear", "slug": "gear"},
        headers=admin_headers,
    )).json()["data"]

    prod = (await client.post(
        "/admin/products",
        json={
            "name": "Hiking Backpack",
            "slug": "hiking-backpack",
            "price": 80.0,
            "stock_qty": 10,
            "category_public_id": cat["public_id"],
        },
        headers=admin_headers,
    )).json()["data"]

    # Add to cart & checkout
    await client.post(
        "/cart/items",
        json={"product_public_id": prod["public_id"], "quantity": 1},
        headers=cust_headers,
    )
    order = (await client.post(
        "/checkout",
        json={
            "phone": "+8801811223344",
            "address": {
                "full_name": "Bob",
                "phone": "+8801811223344",
                "address_line": "Trail Road 10",
                "city": "Sylhet",
                "district": "Sylhet",
            },
        },
        headers=cust_headers,
    )).json()["data"]
    order_pid = order["public_id"]

    # Invalid transition directly from pending to delivered should be rejected
    invalid_res = await client.patch(
        f"/admin/orders/{order_pid}/status",
        json={"status": "delivered"},
        headers=admin_headers,
    )
    assert invalid_res.status_code == 400
    assert invalid_res.json()["code"] == "INVALID_STATUS_TRANSITION"

    # Valid step 1: pending -> confirmed
    s1 = await client.patch(
        f"/admin/orders/{order_pid}/status",
        json={"status": "confirmed", "note": "Payment verified"},
        headers=admin_headers,
    )
    assert s1.status_code == 200
    assert s1.json()["data"]["status"] == "confirmed"

    # Valid step 2: confirmed -> processing
    s2 = await client.patch(
        f"/admin/orders/{order_pid}/status",
        json={"status": "processing"},
        headers=admin_headers,
    )
    assert s2.status_code == 200

    # Valid step 3: processing -> shipped
    s3 = await client.patch(
        f"/admin/orders/{order_pid}/status",
        json={"status": "shipped"},
        headers=admin_headers,
    )
    assert s3.status_code == 200

    # Valid step 4: shipped -> delivered
    s4 = await client.patch(
        f"/admin/orders/{order_pid}/status",
        json={"status": "delivered"},
        headers=admin_headers,
    )
    assert s4.status_code == 200
    assert s4.json()["data"]["status"] == "delivered"
    assert s4.json()["data"]["payment_status"] == "paid"

    # Check status history has all steps recorded
    history = s4.json()["data"]["status_history"]
    assert len(history) == 5
