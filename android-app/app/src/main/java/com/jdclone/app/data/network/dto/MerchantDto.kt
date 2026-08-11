package com.jdclone.app.data.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class MerchantLoginRequest(
    @SerialName("login_name") val loginName: String,
    val password: String,
)

@Serializable
data class MerchantAccountDto(
    val id: Long,
    @SerialName("user_id") val userId: Long,
    @SerialName("login_name") val loginName: String,
    @SerialName("shop_id") val shopId: Long,
    val role: String,
    val status: String,
)

@Serializable
data class MerchantShopDto(
    val id: Long,
    val name: String,
    val description: String? = null,
    @SerialName("contact_name") val contactName: String,
    @SerialName("contact_phone") val contactPhone: String,
    val status: String,
    @SerialName("logo_url") val logoUrl: String? = null,
    @SerialName("banner_url") val bannerUrl: String? = null,
    val announcement: String? = null,
    @SerialName("opened_at") val openedAt: String? = null,
    @SerialName("rating_avg") val ratingAvg: Double = 5.0,
    @SerialName("rating_count") val ratingCount: Int = 0,
    @SerialName("sales_count") val salesCount: Int = 0,
)

@Serializable
data class MerchantAuthTokensDto(
    @SerialName("merchant_account") val merchantAccount: MerchantAccountDto,
    val shop: MerchantShopDto,
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String,
    @SerialName("expires_in") val expiresIn: Int,
)

@Serializable
data class MerchantMeDto(
    @SerialName("merchant_account") val merchantAccount: MerchantAccountDto,
    val shop: MerchantShopDto,
    val permissions: List<String> = emptyList(),
)

@Serializable
data class MerchantOrderStatsDto(
    @SerialName("pending_payment_count") val pendingPaymentCount: Int,
    @SerialName("paid_pending_ship_count") val paidPendingShipCount: Int,
    @SerialName("shipped_count") val shippedCount: Int,
    @SerialName("completed_today_count") val completedTodayCount: Int,
    @SerialName("revenue_today_cents") val revenueTodayCents: Int,
)

@Serializable
data class MerchantAftersalesStatsDto(
    @SerialName("pending_review_count") val pendingReviewCount: Int = 0,
    @SerialName("waiting_receive_count") val waitingReceiveCount: Int = 0,
    @SerialName("waiting_ship_count") val waitingShipCount: Int = 0,
    @SerialName("overdue_soon_count") val overdueSoonCount: Int = 0,
    @SerialName("completed_this_month_count") val completedThisMonthCount: Int = 0,
)
