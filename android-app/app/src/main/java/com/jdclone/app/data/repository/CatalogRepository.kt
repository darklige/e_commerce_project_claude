package com.jdclone.app.data.repository

import com.jdclone.app.data.network.ApiService
import com.jdclone.app.data.network.dto.BrandDto
import com.jdclone.app.data.network.dto.CategoryDto
import com.jdclone.app.data.network.PageData
import com.jdclone.app.data.network.dto.ShopPublicDto
import com.jdclone.app.data.network.dto.SpuDetailDto
import com.jdclone.app.data.network.dto.SpuListItemDto
import com.jdclone.app.data.network.unwrap
import javax.inject.Inject
import javax.inject.Singleton

/** 商品浏览（类目 / 品牌 / SPU / 店铺）—— 全部公开，无需 token。 */
@Singleton
class CatalogRepository @Inject constructor(private val api: ApiService) {

    suspend fun listCategories(): Result<List<CategoryDto>> = safeIo {
        api.listCategories().unwrap().items
    }

    suspend fun listBrands(page: Int = 1, size: Int = 20): Result<PageData<BrandDto>> = safeIo {
        api.listBrands(page = page, size = size).unwrap()
    }

    suspend fun listSpus(
        categoryId: Long? = null,
        brandId: Long? = null,
        keyword: String? = null,
        sort: String = "default",
        page: Int = 1,
        size: Int = 20,
    ): Result<PageData<SpuListItemDto>> = safeIo {
        api.listSpus(
            categoryId = categoryId,
            brandId = brandId,
            keyword = keyword,
            sort = sort,
            page = page,
            size = size,
        ).unwrap()
    }

    suspend fun getSpuDetail(id: Long): Result<SpuDetailDto> = safeIo {
        api.getSpuDetail(id).unwrap()
    }

    suspend fun getRelated(id: Long, limit: Int = 8): Result<List<SpuListItemDto>> = safeIo {
        api.getRelatedSpus(id, limit).unwrap().items
    }

    suspend fun getRecommendations(limit: Int = 10): Result<List<SpuListItemDto>> = safeIo {
        api.getRecommendations(limit).unwrap().items
    }

    suspend fun getShop(id: Long): Result<ShopPublicDto> = safeIo {
        api.getShop(id).unwrap()
    }

    suspend fun listShopSpus(
        shopId: Long,
        page: Int = 1,
        size: Int = 20,
    ): Result<PageData<SpuListItemDto>> = safeIo {
        api.listShopSpus(shopId, page = page, size = size).unwrap()
    }
}
