package com.jdclone.app.data.local

import com.jdclone.app.data.network.dto.MerchantAccountDto
import com.jdclone.app.data.network.dto.MerchantShopDto
import com.jdclone.app.data.network.dto.UserDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

sealed interface SessionPrincipal {
    data class User(val user: UserDto) : SessionPrincipal

    data class Merchant(
        val account: MerchantAccountDto,
        val shop: MerchantShopDto,
        val permissions: List<String>,
    ) : SessionPrincipal
}

sealed interface AuthState {
    data object Loading : AuthState
    data object LoggedOut : AuthState
    data class LoggedIn(val principal: SessionPrincipal) : AuthState
}

@Singleton
class SessionState @Inject constructor() {
    private val _authState = MutableStateFlow<AuthState>(AuthState.Loading)
    val authState: StateFlow<AuthState> = _authState.asStateFlow()

    fun setLoggedInUser(user: UserDto) {
        _authState.value = AuthState.LoggedIn(SessionPrincipal.User(user))
    }

    fun setLoggedInMerchant(
        account: MerchantAccountDto,
        shop: MerchantShopDto,
        permissions: List<String>,
    ) {
        _authState.value = AuthState.LoggedIn(
            SessionPrincipal.Merchant(account = account, shop = shop, permissions = permissions),
        )
    }

    fun setLoggedOut() {
        _authState.value = AuthState.LoggedOut
    }

    fun markInitialized(principal: SessionPrincipal?) {
        _authState.value = if (principal != null) AuthState.LoggedIn(principal) else AuthState.LoggedOut
    }

    fun currentUser(): UserDto? = (authState.value as? AuthState.LoggedIn)
        ?.principal
        ?.let { it as? SessionPrincipal.User }
        ?.user

    fun currentMerchant(): SessionPrincipal.Merchant? = (authState.value as? AuthState.LoggedIn)
        ?.principal
        ?.let { it as? SessionPrincipal.Merchant }
}
