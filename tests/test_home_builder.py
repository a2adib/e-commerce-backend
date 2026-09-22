import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_home_page_builder_and_publish(client: AsyncClient, admin_auth):
    admin_user, admin_headers = admin_auth

    # 1. Admin saves draft home page with discriminated union sections
    sections_payload = [
        {
            "id": "sec_hero",
            "type": "hero_banner",
            "is_visible": True,
            "config": {
                "slides": [
                    {
                        "image_url": "http://example.com/banner.jpg",
                        "title": "Grand Winter Sale",
                        "subtitle": "Up to 50% Off",
                        "cta_text": "Shop Now",
                        "cta_link": "/products",
                    }
                ],
                "autoplay": True,
                "interval_seconds": 6,
            },
        },
        {
            "id": "sec_cat",
            "type": "category_grid",
            "is_visible": True,
            "config": {
                "title": "Shop Top Categories",
                "columns": 3,
                "category_slugs": ["electronics", "fashion"],
            },
        },
    ]

    draft_res = await client.put(
        "/admin/home",
        json={"sections": sections_payload},
        headers=admin_headers,
    )
    assert draft_res.status_code == 200
    assert draft_res.json()["data"]["status"] == "draft"
    assert len(draft_res.json()["data"]["sections"]) == 2

    # 2. Public /home endpoint before publish should still have previous or empty published version
    pub_before = await client.get("/home")
    assert pub_before.status_code == 200

    # 3. Admin publishes home page
    pub_res = await client.post("/admin/home/publish", headers=admin_headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["data"]["status"] == "published"
    assert pub_res.json()["data"]["published_at"] is not None

    # 4. Public /home now returns the published sections
    pub_after = await client.get("/home")
    assert pub_after.status_code == 200
    assert len(pub_after.json()["data"]["sections"]) == 2
    assert pub_after.json()["data"]["sections"][0]["type"] == "hero_banner"
