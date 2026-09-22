import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_product_visibility_and_admin_crud(client: AsyncClient, admin_auth):
    admin_user, admin_headers = admin_auth

    # 1. Admin creates Category
    cat_res = await client.post(
        "/admin/categories",
        json={"name": "Audio", "slug": "audio", "description": "Sound devices"},
        headers=admin_headers,
    )
    assert cat_res.status_code == 201
    cat_pid = cat_res.json()["data"]["public_id"]

    # 2. Admin creates Product
    prod_res = await client.post(
        "/admin/products",
        json={
            "name": "Wireless Earbuds",
            "slug": "wireless-earbuds",
            "price": 49.99,
            "compare_at_price": 69.99,
            "sku": "AUD-EB-01",
            "stock_qty": 15,
            "images": ["http://example.com/earbuds.jpg"],
            "category_public_id": cat_pid,
        },
        headers=admin_headers,
    )
    assert prod_res.status_code == 201
    prod_pid = prod_res.json()["data"]["public_id"]

    # 3. Storefront can view product
    pub_res = await client.get("/products")
    assert pub_res.status_code == 200
    assert len(pub_res.json()["data"]) == 1

    slug_res = await client.get("/products/wireless-earbuds")
    assert slug_res.status_code == 200
    assert slug_res.json()["data"]["name"] == "Wireless Earbuds"

    # 4. Admin toggles product active status -> inactive
    toggle_res = await client.patch(
        f"/admin/products/{prod_pid}/toggle-active",
        headers=admin_headers,
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["data"]["is_active"] is False

    # 5. Storefront can no longer see inactive product
    pub_res_after = await client.get("/products")
    assert len(pub_res_after.json()["data"]) == 0

    slug_res_404 = await client.get("/products/wireless-earbuds")
    assert slug_res_404.status_code == 404
