package com.jdclone.app.data.network

import com.jdclone.app.data.local.AuthSubject
import com.jdclone.app.data.local.AuthTokenManager
import com.jdclone.app.data.local.SessionState
import com.jdclone.app.data.network.dto.RefreshRequest
import com.jdclone.app.data.network.dto.TokenPairDto
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Provider
import javax.inject.Singleton

@Singleton
class AuthInterceptor @Inject constructor(
    private val tokenManager: AuthTokenManager,
    private val session: SessionState,
    private val apiServiceProvider: Provider<ApiService>,
) : Interceptor {

    private val refreshMutex = Mutex()

    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val access = tokenManager.accessBlocking()
        val firstRequest = if (access.isNullOrBlank() || original.header("Authorization") != null) {
            original
        } else {
            original.newBuilder().header("Authorization", "Bearer $access").build()
        }

        val response = chain.proceed(firstRequest)
        if (response.code != 401) return response

        val envelopeCode = peekEnvelopeCode(response)
        if (envelopeCode != 1002) return response

        response.close()

        val newAccess = runBlocking { attemptRefresh() } ?: run {
            runBlocking { tokenManager.clear() }
            session.setLoggedOut()
            return chain.proceed(original)
        }

        val retried = original.newBuilder()
            .header("Authorization", "Bearer $newAccess")
            .build()
        return chain.proceed(retried)
    }

    private suspend fun attemptRefresh(): String? = refreshMutex.withLock {
        val current = tokenManager.access()
        val refresh = tokenManager.refresh()
        val subject = tokenManager.subject()
        if (refresh.isNullOrBlank() || subject == null) return@withLock null
        try {
            val result: TokenPairDto = when (subject) {
                AuthSubject.USER -> apiServiceProvider.get()
                    .refresh(RefreshRequest(refreshToken = refresh))
                    .unwrap()

                AuthSubject.MERCHANT -> apiServiceProvider.get()
                    .merchantRefresh(RefreshRequest(refreshToken = refresh))
                    .unwrap()
            }
            tokenManager.save(access = result.accessToken, refresh = result.refreshToken, subject = subject)
            result.accessToken
        } catch (_: Throwable) {
            val newest = tokenManager.access()
            if (!newest.isNullOrBlank() && newest != current) newest else null
        }
    }

    private fun peekEnvelopeCode(response: Response): Int? {
        val peek = try {
            response.peekBody(1024 * 1024).string()
        } catch (_: Throwable) {
            return null
        }
        val match = Regex("\"code\"\\s*:\\s*(-?\\d+)").find(peek)
        return match?.groupValues?.getOrNull(1)?.toIntOrNull()
    }
}
