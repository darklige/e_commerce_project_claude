package com.jdclone.app.data.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class MerchantSpuCreateRequest(
    @SerialName("category_id") val categoryId: Long,
    @SerialName("brand_id") val brandId: Long? = null,
    val title: String,
    val subtitle: String? = null,
    val description: String? = null,
    @SerialName("main_image") val mainImage: String,
    val images: List<String> = emptyList(),
    @SerialName("spec_axes") val specAxes: List<String> = emptyList(),
)

@Serializable
data class MerchantSpuUpdateRequest(
    @SerialName("category_id") val categoryId: Long? = null,
    @SerialName("brand_id") val brandId: Long? = null,
    val title: String? = null,
    val subtitle: String? = null,
    val description: String? = null,
    @SerialName("main_image") val mainImage: String? = null,
    val images: List<String>? = null,
    @SerialName("spec_axes") val specAxes: List<String>? = null,
)

@Serializable
data class MerchantSkuCreateRequest(
    @SerialName("sku_code") val skuCode: String,
    val specs: Map<String, String> = emptyMap(),
    @SerialName("price_cents") val priceCents: Int,
    @SerialName("original_price_cents") val originalPriceCents: Int? = null,
    val stock: Int = 0,
    val image: String? = null,
    @SerialName("is_active") val isActive: Boolean = true,
)

@Serializable
data class MerchantSkuUpdateRequest(
    @SerialName("price_cents") val priceCents: Int? = null,
    @SerialName("original_price_cents") val originalPriceCents: Int? = null,
    val image: String? = null,
    @SerialName("is_active") val isActive: Boolean? = null,
)

@Serializable
data class MerchantSkuListDto(
    val items: List<SkuDto> = emptyList(),
)

@Serializable
data class MerchantShipRequest(
    val carrier: String,
    @SerialName("tracking_no") val trackingNo: String,
)

@Serializable
data class InventoryAdjustRequest(
    val delta: Int,
    val reason: String,
    val note: String? = null,
)

@Serializable
data class InventoryLogDto(
    val id: Long,
    @SerialName("sku_id") val skuId: Long,
    val delta: Int,
    @SerialName("balance_after") val balanceAfter: Int,
    val reason: String,
    @SerialName("operator_type") val operatorType: String,
    @SerialName("operator_id") val operatorId: Long? = null,
    val note: String? = null,
    @SerialName("related_order_id") val relatedOrderId: Long? = null,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class MerchantReviewReplyDto(
    val id: Long,
    val content: String,
    @SerialName("shop_id") val shopId: Long,
    @SerialName("merchant_account_id") val merchantAccountId: Long,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class MerchantReviewDto(
    val id: Long,
    @SerialName("order_id") val orderId: Long,
    @SerialName("order_item_id") val orderItemId: Long,
    @SerialName("user_id") val userId: Long,
    @SerialName("user_display_name") val userDisplayName: String? = null,
    @SerialName("spu_id") val spuId: Long,
    @SerialName("sku_id") val skuId: Long,
    @SerialName("shop_id") val shopId: Long,
    val rating: Int,
    val content: String,
    val images: List<String> = emptyList(),
    @SerialName("is_anonymous") val isAnonymous: Boolean = false,
    val visible: Boolean = true,
    @SerialName("hidden_reason") val hiddenReason: String? = null,
    @SerialName("edit_count") val editCount: Int = 0,
    @SerialName("edit_deadline_at") val editDeadlineAt: String,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
    val reply: MerchantReviewReplyDto? = null,
)

@Serializable
data class MerchantReviewListDto(
    val items: List<MerchantReviewDto> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    val size: Int = 20,
)

@Serializable
data class ReviewReplyRequest(val content: String)

@Serializable
data class MerchantAftersalesApproveRequest(
    @SerialName("actual_refund_cents") val actualRefundCents: Int,
    @SerialName("return_address") val returnAddress: String? = null,
    @SerialName("review_note") val reviewNote: String? = null,
)

@Serializable
data class MerchantAftersalesRejectRequest(
    @SerialName("review_note") val reviewNote: String,
)

@Serializable
data class MerchantAftersalesConfirmReceiveRequest(
    val note: String? = null,
    @SerialName("evidence_image_keys") val evidenceImageKeys: List<String> = emptyList(),
)

@Serializable
data class MerchantAftersalesRefuseReceiveRequest(
    @SerialName("refuse_note") val refuseNote: String,
    @SerialName("evidence_image_keys") val evidenceImageKeys: List<String> = emptyList(),
)

@Serializable
data class MerchantAftersalesShipExchangeRequest(
    val carrier: String,
    @SerialName("tracking_no") val trackingNo: String,
)

@Serializable
data class MerchantAftersalesNoteRequest(
    val note: String,
)

@Serializable
data class MerchantShopUpdateRequest(
    val description: String? = null,
    @SerialName("contact_name") val contactName: String? = null,
    @SerialName("contact_phone") val contactPhone: String? = null,
    @SerialName("logo_url") val logoUrl: String? = null,
    @SerialName("banner_url") val bannerUrl: String? = null,
    val announcement: String? = null,
)
