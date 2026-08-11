package com.jdclone.app.data.repository

import com.jdclone.app.data.network.ApiService
import com.jdclone.app.data.network.dto.AddressCreateRequest
import com.jdclone.app.data.network.dto.AddressDto
import com.jdclone.app.data.network.dto.AddressUpdateRequest
import com.jdclone.app.data.network.dto.RegionDto
import com.jdclone.app.data.network.unwrap
import com.jdclone.app.data.network.unwrapOptional
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AddressRepository @Inject constructor(private val api: ApiService) {

    suspend fun list(): Result<List<AddressDto>> = safeIo { api.listAddresses().unwrap().items }

    suspend fun get(id: Long): Result<AddressDto> = safeIo { api.getAddress(id).unwrap() }

    suspend fun create(body: AddressCreateRequest): Result<AddressDto> = safeIo {
        api.createAddress(body).unwrap()
    }

    suspend fun update(id: Long, body: AddressUpdateRequest): Result<AddressDto> = safeIo {
        api.updateAddress(id, body).unwrap()
    }

    suspend fun delete(id: Long): Result<Unit> = safeIo {
        api.deleteAddress(id).unwrapOptional()
        Unit
    }

    suspend fun setDefault(id: Long): Result<AddressDto> = safeIo {
        api.setDefaultAddress(id).unwrap()
    }

    suspend fun listRegions(parentCode: String? = null): Result<List<RegionDto>> = safeIo {
        if (parentCode.isNullOrBlank()) {
            api.listTopRegions().unwrap()
        } else {
            api.listRegionChildren(parentCode).unwrap()
        }
    }
}
