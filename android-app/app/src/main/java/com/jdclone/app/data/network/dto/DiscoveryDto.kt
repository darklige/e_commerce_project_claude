package com.jdclone.app.data.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CouponDto(
    val id: String,
    val title: String,
    val subtitle: String,
    @SerialName("discount_label") val discountLabel: String,
    @SerialName("threshold_label") val thresholdLabel: String,
    val claimed: Boolean = false,
    @SerialName("expires_at") val expiresAt: String,
    @SerialName("scope_label") val scopeLabel: String,
)

@Serializable
data class FollowedShopDto(
    val id: Long,
    val name: String,
    val description: String? = null,
    @SerialName("logo_url") val logoUrl: String? = null,
    val announcement: String? = null,
    @SerialName("sales_count") val salesCount: Int = 0,
    @SerialName("rating_avg") val ratingAvg: Double = 5.0,
    @SerialName("rating_count") val ratingCount: Int = 0,
    val followed: Boolean = true,
)

@Serializable
data class FavoriteSpuDto(
    val spu: SpuListItemDto,
    @SerialName("collected_at") val collectedAt: String,
)

@Serializable
data class FootprintDto(
    val spu: SpuListItemDto,
    @SerialName("viewed_at") val viewedAt: String,
)

@Serializable
data class CampaignSectionDto(
    val title: String,
    val subtitle: String,
    val items: List<SpuListItemDto> = emptyList(),
)

@Serializable
data class CampaignDto(
    val id: String,
    val title: String,
    val subtitle: String,
    @SerialName("banner_text") val bannerText: String,
    @SerialName("start_at") val startAt: String,
    @SerialName("end_at") val endAt: String,
    @SerialName("full_reduction_rules") val fullReductionRules: List<String> = emptyList(),
    val coupons: List<CouponDto> = emptyList(),
    @SerialName("featured_sections") val featuredSections: List<CampaignSectionDto> = emptyList(),
    @SerialName("featured_shop") val featuredShop: ShopBriefDto? = null,
)

@Serializable
data class EngagementOverviewDto(
    @SerialName("coupon_count") val couponCount: Int,
    @SerialName("favorite_count") val favoriteCount: Int,
    @SerialName("follow_count") val followCount: Int,
    @SerialName("footprint_count") val footprintCount: Int,
    val headline: String,
    @SerialName("active_campaign") val activeCampaign: CampaignDto? = null,
)

@Serializable
data class ToggleResultDto(
    val active: Boolean,
    val total: Int,
)
