import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cart_wishlist_and_addresses(client: AsyncClient, customer_auth, admin_auth):
    cust_user, cust_headers = customer_auth
    admin_user, admin_headers = admin_auth

    # Admin creates Category and Product
    cat = (await client.post(
        "/admin/categories",
        json={"name": "Books", "slug": "books"},
        headers=admin_headers,
    )).json()["data"]

    prod = (await client.post(
        "/admin/products",
        json={
            "name": "Clean Code",
            "slug": "clean-code",
            "price": 30.0,
            "stock_qty": 5,
            "category_public_id": cat["public_id"],
        },
        headers=admin_headers,
    )).json()["data"]

    # 1. Customer adds to cart
    cart_res = await client.post(
        "/cart/items",
        json={"product_public_id": prod["public_id"], "quantity": 2},
        headers=cust_headers,
    )
    assert cart_res.status_code == 200
    cart_data = cart_res.json()["data"]
    assert cart_data["total_items"] == 2
    assert cart_data["subtotal"] == 60.0
    item_pid = cart_data["items"][0]["public_id"]

    # 2. Update cart item quantity
    patch_res = await client.patch(
        f"/cart/items/{item_pid}",
        json={"quantity": 3},
        headers=cust_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["total_items"] == 3

    # Exceeding stock fails
    exceed_res = await client.patch(
        f"/cart/items/{item_pid}",
        json={"quantity": 10},
        headers=cust_headers,
    )
    assert exceed_res.status_code == 400
    assert exceed_res.json()["code"] == "INSUFFICIENT_STOCK"

    # 3. Wishlist add and get
    wish_res = await client.post(
        f"/wishlist/{prod['public_id']}",
        headers=cust_headers,
    )
    assert wish_res.status_code == 200

    wish_list = await client.get("/wishlist", headers=cust_headers)
    assert wish_list.status_code == 200
    assert len(wish_list.json()["data"]) == 1

    # 4. Address CRUD
    addr_res = await client.post(
        "/addresses",
        json={
            "full_name": "John Customer",
            "phone": "+8801900000000",
            "address_line": "123 Tech Road",
            "city": "Dhaka",
            "district": "Dhaka",
            "postal_code": "1212",
            "is_default": True,
        },
        headers=cust_headers,
    )
    assert addr_res.status_code == 201
    addr_pid = addr_res.json()["data"]["public_id"]

    addrs = await client.get("/addresses", headers=cust_headers)
    assert len(addrs.json()["data"]) == 1
    assert addrs.json()["data"][0]["public_id"] == addr_pid
