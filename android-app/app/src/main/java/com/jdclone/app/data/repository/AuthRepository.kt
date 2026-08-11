package com.jdclone.app.data.repository

import com.jdclone.app.data.local.AuthSubject
import com.jdclone.app.data.local.AuthTokenManager
import com.jdclone.app.data.local.SessionPrincipal
import com.jdclone.app.data.local.SessionState
import com.jdclone.app.data.network.ApiException
import com.jdclone.app.data.network.ApiService
import com.jdclone.app.data.network.dto.ChangePasswordRequest
import com.jdclone.app.data.network.dto.ForgotPasswordRequest
import com.jdclone.app.data.network.dto.LoginRequest
import com.jdclone.app.data.network.dto.LogoutRequest
import com.jdclone.app.data.network.dto.RegisterRequest
import com.jdclone.app.data.network.dto.ResetPasswordRequest
import com.jdclone.app.data.network.dto.UpdateProfileRequest
import com.jdclone.app.data.network.dto.UserDto
import com.jdclone.app.data.network.dto.UserMeDto
import com.jdclone.app.data.network.unwrap
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val api: ApiService,
    private val tokens: AuthTokenManager,
    private val session: SessionState,
) {
    suspend fun bootstrap(): Result<UserDto?> = safeIo {
        val access = tokens.access()
        val subject = tokens.subject()
        if (access.isNullOrBlank() || subject == null) {
            session.markInitialized(principal = null)
            return@safeIo null
        }
        try {
            when (subject) {
                AuthSubject.USER -> {
                    val me = api.getMe().unwrap()
                    session.markInitialized(SessionPrincipal.User(me.user))
                    me.user
                }

                AuthSubject.MERCHANT -> {
                    val me = api.getMerchantMe().unwrap()
                    session.markInitialized(
                        SessionPrincipal.Merchant(
                            account = me.merchantAccount,
                            shop = me.shop,
                            permissions = me.permissions,
                        ),
                    )
                    null
                }
            }
        } catch (_: Throwable) {
            tokens.clear()
            session.markInitialized(principal = null)
            null
        }
    }

    suspend fun login(identifier: String, password: String): Result<UserDto> = safeIo {
        val result = api.login(LoginRequest(identifier = identifier, password = password)).unwrap()
        tokens.save(result.accessToken, result.refreshToken, AuthSubject.USER)
        session.setLoggedInUser(result.user)
        result.user
    }

    suspend fun register(
        phone: String?,
        email: String?,
        password: String,
        nickname: String?,
    ): Result<UserDto> = safeIo {
        val result = api.register(
            RegisterRequest(
                phone = phone?.takeIf { it.isNotBlank() },
                email = email?.takeIf { it.isNotBlank() },
                password = password,
                nickname = nickname?.takeIf { it.isNotBlank() },
            ),
        ).unwrap()
        tokens.save(result.accessToken, result.refreshToken, AuthSubject.USER)
        session.setLoggedInUser(result.user)
        result.user
    }

    suspend fun forgotPassword(identifier: String): Result<Unit> = safeIo {
        api.forgotPassword(ForgotPasswordRequest(identifier))
        Unit
    }

    suspend fun resetPassword(
        identifier: String,
        code: String,
        newPassword: String,
    ): Result<Unit> = safeIo {
        api.resetPassword(ResetPasswordRequest(identifier, code, newPassword))
        Unit
    }

    suspend fun changePassword(oldPassword: String, newPassword: String): Result<Unit> = safeIo {
        api.changePassword(ChangePasswordRequest(oldPassword, newPassword))
        Unit
    }

    suspend fun me(): Result<UserMeDto> = safeIo { api.getMe().unwrap() }

    suspend fun updateProfile(
        nickname: String? = null,
        avatarUrl: String? = null,
    ): Result<UserMeDto> = safeIo {
        val result = api.updateMe(UpdateProfileRequest(nickname, avatarUrl)).unwrap()
        session.setLoggedInUser(result.user)
        result
    }

    suspend fun logout(): Result<Unit> = safeIo {
        val refresh = tokens.refresh()
        val subject = tokens.subject()
        runCatching {
            when (subject) {
                AuthSubject.MERCHANT -> api.merchantLogout(LogoutRequest(refreshToken = refresh))
                else -> api.logout(LogoutRequest(refreshToken = refresh))
            }
        }
        tokens.clear()
        session.setLoggedOut()
    }
}

internal suspend inline fun <T> safeIo(crossinline block: suspend () -> T): Result<T> =
    withContext(Dispatchers.IO) {
        try {
            Result.success(block())
        } catch (e: ApiException) {
            Result.failure(e)
        } catch (e: Throwable) {
            Result.failure(e)
        }
    }
