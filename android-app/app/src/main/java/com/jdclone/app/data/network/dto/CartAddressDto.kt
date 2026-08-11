package com.jdclone.app.data.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ─────────────────────────────────────────────────────────────────────────────
// Cart
// ─────────────────────────────────────────────────────────────────────────────

@Serializable
data class CartSkuBriefDto(
    val id: Long,
    @SerialName("spu_id") val spuId: Long,
    @SerialName("sku_code") val skuCode: String = "",
    val specs: Map<String, String> = emptyMap(),
    @SerialName("price_cents") val priceCents: Int,
    @SerialName("original_price_cents") val originalPriceCents: Int? = null,
    val stock: Int = 0,
    val image: String? = null,
    @SerialName("is_active") val isActive: Boolean = true,
)

@Serializable
data class CartSpuBriefDto(
    val id: Long,
    val title: String,
    @SerialName("main_image") val mainImage: String,
    val status: String = "approved",
)

@Serializable
data class AddressListPayloadDto(
    val items: List<AddressDto> = emptyList(),
    val total: Int = 0,
)

@Serializable
data class CartShopBriefDto(
    val id: Long,
    val name: String,
)

@Serializable
data class CartItemDto(
    val id: Long,
    @SerialName("sku_id") val skuId: Long,
    val quantity: Int,
    val selected: Boolean,
    val status: String = "valid",
    @SerialName("invalid_reason") val invalidReason: String? = null,
    val sku: CartSkuBriefDto,
    val spu: CartSpuBriefDto,
)

@Serializable
data class CartGroupDto(
    val shop: CartShopBriefDto,
    val items: List<CartItemDto> = emptyList(),
    @SerialName("subtotal_cents_selected") val subtotalCentsSelected: Int = 0,
)

@Serializable
data class CartResponseDto(
    val groups: List<CartGroupDto> = emptyList(),
    @SerialName("total_cents_selected") val totalCentsSelected: Int = 0,
    @SerialName("total_selected_count") val totalSelectedCount: Int = 0,
    @SerialName("invalid_count") val invalidCount: Int = 0,
)

@Serializable
data class CartAddRequest(
    @SerialName("sku_id") val skuId: Long,
    val quantity: Int = 1,
)

@Serializable
data class CartUpdateRequest(
    val quantity: Int? = null,
    val selected: Boolean? = null,
)

@Serializable
data class CartBatchDeleteRequest(val ids: List<Long>)

@Serializable
data class CartSelectAllRequest(val selected: Boolean)

// ─────────────────────────────────────────────────────────────────────────────
// Address / Region
// ─────────────────────────────────────────────────────────────────────────────

@Serializable
data class AddressDto(
    val id: Long,
    @SerialName("user_id") val userId: Long = 0,
    @SerialName("receiver_name") val receiverName: String,
    @SerialName("receiver_phone") val receiverPhone: String,
    val province: String,
    val city: String,
    val district: String,
    val detail: String,
    @SerialName("postal_code") val postalCode: String? = null,
    @SerialName("is_default") val isDefault: Boolean = false,
    @SerialName("province_code") val provinceCode: String? = null,
    @SerialName("city_code") val cityCode: String? = null,
    @SerialName("district_code") val districtCode: String? = null,
)

@Serializable
data class AddressCreateRequest(
    @SerialName("receiver_name") val receiverName: String,
    @SerialName("receiver_phone") val receiverPhone: String,
    val province: String,
    val city: String,
    val district: String,
    val detail: String,
    @SerialName("postal_code") val postalCode: String? = null,
    @SerialName("is_default") val isDefault: Boolean = false,
    @SerialName("province_code") val provinceCode: String? = null,
    @SerialName("city_code") val cityCode: String? = null,
    @SerialName("district_code") val districtCode: String? = null,
)

@Serializable
data class AddressUpdateRequest(
    @SerialName("receiver_name") val receiverName: String? = null,
    @SerialName("receiver_phone") val receiverPhone: String? = null,
    val province: String? = null,
    val city: String? = null,
    val district: String? = null,
    val detail: String? = null,
    @SerialName("postal_code") val postalCode: String? = null,
    @SerialName("is_default") val isDefault: Boolean? = null,
    @SerialName("province_code") val provinceCode: String? = null,
    @SerialName("city_code") val cityCode: String? = null,
    @SerialName("district_code") val districtCode: String? = null,
)
