package com.jdclone.app.data.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ─────────────────────────────────────────────────────────────────────────────
// Catalog / Category / Brand / SPU / SKU / Shop / Region
// ─────────────────────────────────────────────────────────────────────────────

@Serializable
data class CategoryTreePayloadDto(
    val items: List<CategoryDto> = emptyList(),
)

@Serializable
data class SpuListPayloadDto(
    val items: List<SpuListItemDto> = emptyList(),
)

@Serializable
data class CategoryDto(
    val id: Long,
    @SerialName("parent_id") val parentId: Long? = null,
    val name: String,
    val slug: String = "",
    val level: Int = 1,
    val path: String = "",
    @SerialName("icon_url") val iconUrl: String? = null,
    @SerialName("sort_order") val sortOrder: Int = 0,
    @SerialName("is_visible") val isVisible: Boolean = true,
    val children: List<CategoryDto> = emptyList(),
)

@Serializable
data class BrandDto(
    val id: Long,
    val name: String,
    val slug: String,
    @SerialName("logo_url") val logoUrl: String? = null,
    val description: String? = null,
    @SerialName("sort_order") val sortOrder: Int = 0,
    @SerialName("is_visible") val isVisible: Boolean = true,
)

@Serializable
data class BrandBriefDto(
    val id: Long,
    val name: String,
    val slug: String = "",
    @SerialName("logo_url") val logoUrl: String? = null,
)

@Serializable
data class CategoryBriefDto(
    val id: Long,
    val name: String,
    val slug: String = "",
)

@Serializable
data class CategoryPathNode(
    val id: Long,
    val name: String,
    val slug: String = "",
)

@Serializable
data class ShopBriefDto(
    val id: Long,
    val name: String,
)

@Serializable
data class SpuListItemDto(
    val id: Long,
    val title: String,
    val subtitle: String? = null,
    @SerialName("main_image") val mainImage: String,
    @SerialName("min_price_cents") val minPriceCents: Int,
    @SerialName("max_price_cents") val maxPriceCents: Int,
    @SerialName("sales_count") val salesCount: Int = 0,
    val brand: BrandBriefDto? = null,
    val category: CategoryBriefDto? = null,
)

@Serializable
data class SkuDto(
    val id: Long,
    @SerialName("spu_id") val spuId: Long,
    @SerialName("sku_code") val skuCode: String,
    val specs: Map<String, String> = emptyMap(),
    @SerialName("price_cents") val priceCents: Int,
    @SerialName("original_price_cents") val originalPriceCents: Int? = null,
    val stock: Int = 0,
    @SerialName("locked_stock") val lockedStock: Int = 0,
    @SerialName("sold_count") val soldCount: Int = 0,
    val image: String? = null,
    @SerialName("is_active") val isActive: Boolean = true,
)

@Serializable
data class SpuDetailDto(
    val id: Long,
    @SerialName("shop_id") val shopId: Long,
    @SerialName("category_id") val categoryId: Long,
    @SerialName("brand_id") val brandId: Long? = null,
    val title: String,
    val subtitle: String? = null,
    val description: String? = null,
    @SerialName("main_image") val mainImage: String,
    val images: List<String> = emptyList(),
    @SerialName("spec_axes") val specAxes: List<String> = emptyList(),
    val status: String,
    @SerialName("sales_count") val salesCount: Int = 0,
    @SerialName("view_count") val viewCount: Int = 0,
    @SerialName("min_price_cents") val minPriceCents: Int = 0,
    @SerialName("max_price_cents") val maxPriceCents: Int = 0,
    @SerialName("published_at") val publishedAt: String? = null,
    val brand: BrandBriefDto? = null,
    val category: CategoryBriefDto? = null,
    @SerialName("category_path") val categoryPath: List<CategoryPathNode> = emptyList(),
    val shop: ShopBriefDto? = null,
    val skus: List<SkuDto> = emptyList(),
)

@Serializable
data class ShopPublicDto(
    val id: Long,
    val name: String,
    val description: String? = null,
    @SerialName("logo_url") val logoUrl: String? = null,
    @SerialName("banner_url") val bannerUrl: String? = null,
    val announcement: String? = null,
    @SerialName("opened_at") val openedAt: String? = null,
    @SerialName("rating_avg") val ratingAvg: Double = 5.0,
    @SerialName("rating_count") val ratingCount: Int = 0,
    @SerialName("sales_count") val salesCount: Int = 0,
    @SerialName("contact_name") val contactName: String = "",
    @SerialName("contact_phone") val contactPhone: String = "",
    val status: String = "active",
)

@Serializable
data class RegionDto(
    val code: String,
    @SerialName("parent_code") val parentCode: String? = null,
    val name: String,
    @SerialName("short_name") val shortName: String? = null,
    val level: Int,
    @SerialName("sort_order") val sortOrder: Int = 0,
    val children: List<RegionDto> = emptyList(),
)
