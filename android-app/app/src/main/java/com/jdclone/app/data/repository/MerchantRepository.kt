package com.jdclone.app.data.repository

import com.jdclone.app.data.local.AuthSubject
import com.jdclone.app.data.local.AuthTokenManager
import com.jdclone.app.data.local.SessionState
import com.jdclone.app.data.network.ApiService
import com.jdclone.app.data.network.PageData
import com.jdclone.app.data.network.dto.AftersalesDetailDto
import com.jdclone.app.data.network.dto.AftersalesListItemDto
import com.jdclone.app.data.network.dto.InventoryAdjustRequest
import com.jdclone.app.data.network.dto.InventoryLogDto
import com.jdclone.app.data.network.dto.MerchantAftersalesApproveRequest
import com.jdclone.app.data.network.dto.MerchantAftersalesConfirmReceiveRequest
import com.jdclone.app.data.network.dto.MerchantAftersalesNoteRequest
import com.jdclone.app.data.network.dto.MerchantAftersalesRefuseReceiveRequest
import com.jdclone.app.data.network.dto.MerchantAftersalesRejectRequest
import com.jdclone.app.data.network.dto.MerchantAftersalesShipExchangeRequest
import com.jdclone.app.data.network.dto.MerchantAftersalesStatsDto
import com.jdclone.app.data.network.dto.MerchantLoginRequest
import com.jdclone.app.data.network.dto.MerchantMeDto
import com.jdclone.app.data.network.dto.MerchantOrderStatsDto
import com.jdclone.app.data.network.dto.MerchantReviewListDto
import com.jdclone.app.data.network.dto.MerchantShipRequest
import com.jdclone.app.data.network.dto.MerchantShopUpdateRequest
import com.jdclone.app.data.network.dto.MerchantSkuCreateRequest
import com.jdclone.app.data.network.dto.MerchantSkuUpdateRequest
import com.jdclone.app.data.network.dto.MerchantSpuCreateRequest
import com.jdclone.app.data.network.dto.MerchantSpuUpdateRequest
import com.jdclone.app.data.network.dto.NotificationListDto
import com.jdclone.app.data.network.dto.OrderDetailDto
import com.jdclone.app.data.network.dto.OrderListItemDto
import com.jdclone.app.data.network.dto.ReviewReplyRequest
import com.jdclone.app.data.network.dto.SkuDto
import com.jdclone.app.data.network.dto.SpuDetailDto
import com.jdclone.app.data.network.dto.SpuListItemDto
import com.jdclone.app.data.network.unwrap
import com.jdclone.app.data.network.unwrapOptional
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MerchantRepository @Inject constructor(
    private val api: ApiService,
    private val tokens: AuthTokenManager,
    private val session: SessionState,
) {
    suspend fun login(loginName: String, password: String): Result<MerchantMeDto> = safeIo {
        val result = api.merchantLogin(MerchantLoginRequest(loginName, password)).unwrap()
        tokens.save(result.accessToken, result.refreshToken, AuthSubject.MERCHANT)
        session.setLoggedInMerchant(
            account = result.merchantAccount,
            shop = result.shop,
            permissions = emptyList(),
        )
        val me = api.getMerchantMe().unwrap()
        session.setLoggedInMerchant(
            account = me.merchantAccount,
            shop = me.shop,
            permissions = me.permissions,
        )
        me
    }

    suspend fun me(): Result<MerchantMeDto> = safeIo { api.getMerchantMe().unwrap() }

    suspend fun listOrders(
        status: String? = null,
        keyword: String? = null,
        page: Int = 1,
        size: Int = 20,
    ): Result<PageData<OrderListItemDto>> = safeIo {
        api.listMerchantOrders(status = status, keyword = keyword, page = page, size = size).unwrap()
    }

    suspend fun getOrderStats(): Result<MerchantOrderStatsDto> = safeIo {
        api.getMerchantOrderStats().unwrap()
    }

    suspend fun getOrder(id: Long): Result<OrderDetailDto> = safeIo {
        api.getMerchantOrder(id).unwrap()
    }

    suspend fun cancelOrder(id: Long, cancelNote: String): Result<OrderDetailDto> = safeIo {
        api.cancelMerchantOrder(id, com.jdclone.app.data.network.dto.OrderCancelRequest(cancelNote)).unwrap()
    }

    suspend fun shipOrder(id: Long, carrier: String, trackingNo: String): Result<OrderDetailDto> = safeIo {
        api.shipMerchantOrder(id, MerchantShipRequest(carrier = carrier, trackingNo = trackingNo)).unwrap()
    }

    suspend fun listAftersales(
        status: String? = null,
        type: String? = null,
        keyword: String? = null,
        page: Int = 1,
        size: Int = 20,
    ): Result<PageData<AftersalesListItemDto>> = safeIo {
        api.listMerchantAftersales(status = status, type = type, keyword = keyword, page = page, size = size).unwrap()
    }

    suspend fun getAftersalesStats(): Result<MerchantAftersalesStatsDto> = safeIo {
        api.getMerchantAftersalesStats().unwrap()
    }

    suspend fun getAftersales(id: Long): Result<AftersalesDetailDto> = safeIo {
        api.getMerchantAftersales(id).unwrap()
    }

    suspend fun approveAftersales(
        id: Long,
        actualRefundCents: Int,
        returnAddress: String,
        reviewNote: String,
    ): Result<AftersalesDetailDto> = safeIo {
        api.approveMerchantAftersales(
            id,
            MerchantAftersalesApproveRequest(
                actualRefundCents = actualRefundCents,
                returnAddress = returnAddress.ifBlank { null },
                reviewNote = reviewNote.ifBlank { null },
            ),
        ).unwrap()
    }

    suspend fun rejectAftersales(id: Long, reviewNote: String): Result<AftersalesDetailDto> = safeIo {
        api.rejectMerchantAftersales(id, MerchantAftersalesRejectRequest(reviewNote)).unwrap()
    }

    suspend fun confirmAftersalesReceived(id: Long, note: String): Result<AftersalesDetailDto> = safeIo {
        api.confirmMerchantAftersalesReceived(
            id,
            MerchantAftersalesConfirmReceiveRequest(note = note.ifBlank { null }),
        ).unwrap()
    }

    suspend fun refuseAftersalesReceive(id: Long, note: String): Result<AftersalesDetailDto> = safeIo {
        api.refuseMerchantAftersalesReceive(id, MerchantAftersalesRefuseReceiveRequest(note)).unwrap()
    }

    suspend fun shipAftersalesExchange(id: Long, carrier: String, trackingNo: String): Result<AftersalesDetailDto> = safeIo {
        api.shipMerchantAftersalesExchange(
            id,
            MerchantAftersalesShipExchangeRequest(carrier = carrier, trackingNo = trackingNo),
        ).unwrap()
    }

    suspend fun noteAftersales(id: Long, note: String): Result<AftersalesDetailDto> = safeIo {
        api.noteMerchantAftersales(id, MerchantAftersalesNoteRequest(note)).unwrap()
    }

    suspend fun listSpus(
        status: String? = null,
        keyword: String? = null,
        page: Int = 1,
        size: Int = 20,
    ): Result<PageData<SpuListItemDto>> = safeIo {
        api.listMerchantSpus(status = status, keyword = keyword, page = page, size = size).unwrap()
    }

    suspend fun getSpu(id: Long): Result<SpuDetailDto> = safeIo { api.getMerchantSpu(id).unwrap() }

    suspend fun createSpu(
        categoryId: Long,
        brandId: Long?,
        title: String,
        subtitle: String,
        description: String,
        mainImage: String,
    ): Result<SpuDetailDto> = safeIo {
        api.createMerchantSpu(
            MerchantSpuCreateRequest(
                categoryId = categoryId,
                brandId = brandId,
                title = title,
                subtitle = subtitle.ifBlank { null },
                description = description.ifBlank { null },
                mainImage = mainImage,
            ),
        ).unwrap()
    }

    suspend fun updateSpu(
        id: Long,
        categoryId: Long,
        brandId: Long?,
        title: String,
        subtitle: String,
        description: String,
        mainImage: String,
    ): Result<SpuDetailDto> = safeIo {
        api.updateMerchantSpu(
            id,
            MerchantSpuUpdateRequest(
                categoryId = categoryId,
                brandId = brandId,
                title = title,
                subtitle = subtitle.ifBlank { null },
                description = description.ifBlank { null },
                mainImage = mainImage,
            ),
        ).unwrap()
    }

    suspend fun deleteSpu(id: Long): Result<Unit> = safeIo {
        api.deleteMerchantSpu(id).unwrapOptional()
        Unit
    }

    suspend fun submitReview(id: Long): Result<SpuDetailDto> = safeIo {
        api.submitMerchantSpuReview(id).unwrap()
    }

    suspend fun withdrawReview(id: Long): Result<SpuDetailDto> = safeIo {
        api.withdrawMerchantSpuReview(id).unwrap()
    }

    suspend fun onshelf(id: Long): Result<SpuDetailDto> = safeIo {
        api.onshelfMerchantSpu(id).unwrap()
    }

    suspend fun offshelf(id: Long): Result<SpuDetailDto> = safeIo {
        api.offshelfMerchantSpu(id).unwrap()
    }

    suspend fun adjustInventory(skuId: Long, delta: Int, note: String): Result<InventoryLogDto> = safeIo {
        api.adjustMerchantInventory(
            skuId,
            InventoryAdjustRequest(delta = delta, reason = "manual_adjust", note = note),
        ).unwrap()
    }

    suspend fun listInventoryLogs(
        skuId: Long,
        page: Int = 1,
        size: Int = 20,
    ): Result<PageData<InventoryLogDto>> = safeIo {
        api.listMerchantInventoryLogs(skuId, page = page, size = size).unwrap()
    }

    suspend fun listSkus(spuId: Long): Result<List<SkuDto>> = safeIo {
        api.listMerchantSkus(spuId).unwrap().items
    }

    suspend fun createSku(
        spuId: Long,
        skuCode: String,
        specs: Map<String, String>,
        priceCents: Int,
        originalPriceCents: Int?,
        stock: Int,
        image: String,
    ): Result<SkuDto> = safeIo {
        api.createMerchantSku(
            spuId,
            MerchantSkuCreateRequest(
                skuCode = skuCode,
                specs = specs,
                priceCents = priceCents,
                originalPriceCents = originalPriceCents,
                stock = stock,
                image = image.ifBlank { null },
            ),
        ).unwrap()
    }

    suspend fun updateSku(
        spuId: Long,
        skuId: Long,
        priceCents: Int,
        originalPriceCents: Int?,
        image: String,
        isActive: Boolean,
    ): Result<SkuDto> = safeIo {
        api.updateMerchantSku(
            spuId,
            skuId,
            MerchantSkuUpdateRequest(
                priceCents = priceCents,
                originalPriceCents = originalPriceCents,
                image = image.ifBlank { null },
                isActive = isActive,
            ),
        ).unwrap()
    }

    suspend fun deleteSku(spuId: Long, skuId: Long): Result<Unit> = safeIo {
        api.deleteMerchantSku(spuId, skuId).unwrapOptional()
        Unit
    }

    suspend fun listNotifications(page: Int = 1, size: Int = 20): Result<NotificationListDto> = safeIo {
        api.listMerchantNotifications(page = page, size = size).unwrap()
    }

    suspend fun markAllNotificationsRead(): Result<Unit> = safeIo {
        api.markAllMerchantNotificationsRead().unwrapOptional()
        Unit
    }

    suspend fun listReviews(
        hasReply: Boolean? = null,
        page: Int = 1,
        size: Int = 20,
    ): Result<MerchantReviewListDto> = safeIo {
        api.listMerchantReviews(hasReply = hasReply, page = page, size = size).unwrap()
    }

    suspend fun replyReview(reviewId: Long, content: String, hasReply: Boolean): Result<Unit> = safeIo {
        if (hasReply) {
            api.updateMerchantReviewReply(reviewId, ReviewReplyRequest(content)).unwrap()
        } else {
            api.createMerchantReviewReply(reviewId, ReviewReplyRequest(content)).unwrap()
        }
        Unit
    }

    suspend fun updateShop(
        description: String,
        announcement: String,
        contactName: String,
        contactPhone: String,
    ): Result<MerchantMeDto> = safeIo {
        val result = api.updateMerchantShop(
            MerchantShopUpdateRequest(
                description = description,
                announcement = announcement,
                contactName = contactName,
                contactPhone = contactPhone,
            ),
        ).unwrap()
        session.setLoggedInMerchant(
            account = result.merchantAccount,
            shop = result.shop,
            permissions = result.permissions,
        )
        result
    }
}
