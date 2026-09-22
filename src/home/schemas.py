from typing import List, Literal, Optional, Union, Annotated
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# 1. Hero Banner
class HeroSlide(BaseModel):
    image_url: str
    title: str
    subtitle: Optional[str] = None
    cta_text: Optional[str] = None
    cta_link: Optional[str] = None


class HeroBannerConfig(BaseModel):
    slides: List[HeroSlide]
    autoplay: bool = True
    interval_seconds: int = 5


class HeroBannerSection(BaseModel):
    id: str
    type: Literal["hero_banner"] = "hero_banner"
    is_visible: bool = True
    config: HeroBannerConfig


# 2. Category Grid
class CategoryGridConfig(BaseModel):
    category_slugs: List[str] = []
    columns: int = 4
    title: Optional[str] = "Shop by Category"


class CategoryGridSection(BaseModel):
    id: str
    type: Literal["category_grid"] = "category_grid"
    is_visible: bool = True
    config: CategoryGridConfig


# 3. Product Carousel
class ProductCarouselConfig(BaseModel):
    title: str
    source: Literal["manual", "category", "latest"] = "latest"
    product_ids: Optional[List[str]] = None
    category_slug: Optional[str] = None
    limit: int = 10


class ProductCarouselSection(BaseModel):
    id: str
    type: Literal["product_carousel"] = "product_carousel"
    is_visible: bool = True
    config: ProductCarouselConfig


# 4. Promo Banner
class PromoBannerConfig(BaseModel):
    image_url: str
    title: Optional[str] = None
    subtitle: Optional[str] = None
    link: Optional[str] = None


class PromoBannerSection(BaseModel):
    id: str
    type: Literal["promo_banner"] = "promo_banner"
    is_visible: bool = True
    config: PromoBannerConfig


# 5. Rich Text
class RichTextConfig(BaseModel):
    heading: Optional[str] = None
    body_html_or_markdown: str


class RichTextSection(BaseModel):
    id: str
    type: Literal["rich_text"] = "rich_text"
    is_visible: bool = True
    config: RichTextConfig


# 6. Featured Products
class FeaturedProductsConfig(BaseModel):
    title: str = "Featured Products"
    limit: int = 8


class FeaturedProductsSection(BaseModel):
    id: str
    type: Literal["featured_products"] = "featured_products"
    is_visible: bool = True
    config: FeaturedProductsConfig


# Discriminated Union for Section
SectionItem = Annotated[
    Union[
        HeroBannerSection,
        CategoryGridSection,
        ProductCarouselSection,
        PromoBannerSection,
        RichTextSection,
        FeaturedProductsSection,
    ],
    Field(discriminator="type"),
]


class HomePageUpdate(BaseModel):
    sections: List[SectionItem]


class HomePageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    status: str
    sections: List[dict]
    updated_at: datetime
    published_at: Optional[datetime] = None
