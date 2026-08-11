package com.jdclone.app.data.repository

import com.jdclone.app.data.network.ApiService
import com.jdclone.app.data.network.dto.CampaignDto
import com.jdclone.app.data.network.dto.CouponDto
import com.jdclone.app.data.network.dto.EngagementOverviewDto
import com.jdclone.app.data.network.dto.FavoriteSpuDto
import com.jdclone.app.data.network.dto.FollowedShopDto
import com.jdclone.app.data.network.dto.FootprintDto
import com.jdclone.app.data.network.dto.ToggleResultDto
import com.jdclone.app.data.network.unwrap
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DiscoveryRepository @Inject constructor(
    private val api: ApiService,
) {
    suspend fun getOverview(): Result<EngagementOverviewDto> = safeIo {
        api.getEngagementOverview().unwrap()
    }

    suspend fun getActiveCampaign(): Result<CampaignDto> = safeIo {
        api.getActiveCampaign().unwrap()
    }

    suspend fun listCoupons(): Result<List<CouponDto>> = safeIo {
        api.listCoupons().unwrap()
    }

    suspend fun claimCoupon(id: String): Result<CouponDto> = safeIo {
        api.claimCoupon(id).unwrap()
    }

    suspend fun listFavorites(): Result<List<FavoriteSpuDto>> = safeIo {
        api.listFavorites().unwrap()
    }

    suspend fun toggleFavorite(spuId: Long): Result<ToggleResultDto> = safeIo {
        api.toggleFavorite(spuId).unwrap()
    }

    suspend fun listFollows(): Result<List<FollowedShopDto>> = safeIo {
        api.listFollows().unwrap()
    }

    suspend fun toggleFollow(shopId: Long): Result<ToggleResultDto> = safeIo {
        api.toggleFollow(shopId).unwrap()
    }

    suspend fun listFootprints(): Result<List<FootprintDto>> = safeIo {
        api.listFootprints().unwrap()
    }

    suspend fun recordFootprint(spuId: Long): Result<ToggleResultDto> = safeIo {
        api.recordFootprint(spuId).unwrap()
    }
}
