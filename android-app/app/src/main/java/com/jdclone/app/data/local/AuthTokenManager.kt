package com.jdclone.app.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.authDataStore: DataStore<Preferences> by preferencesDataStore(name = "auth")

enum class AuthSubject {
    USER,
    MERCHANT,
}

@Singleton
class AuthTokenManager @Inject constructor(
    @ApplicationContext private val ctx: Context,
) {
    private object Keys {
        val ACCESS = stringPreferencesKey("access_token")
        val REFRESH = stringPreferencesKey("refresh_token")
        val SUBJECT = stringPreferencesKey("auth_subject")
    }

    val accessFlow: Flow<String?> = ctx.authDataStore.data.map { it[Keys.ACCESS] }
    val refreshFlow: Flow<String?> = ctx.authDataStore.data.map { it[Keys.REFRESH] }
    val subjectFlow: Flow<AuthSubject?> = ctx.authDataStore.data.map {
        it[Keys.SUBJECT]?.let(AuthSubject::valueOf)
    }

    suspend fun save(access: String, refresh: String, subject: AuthSubject) {
        ctx.authDataStore.edit { prefs ->
            prefs[Keys.ACCESS] = access
            prefs[Keys.REFRESH] = refresh
            prefs[Keys.SUBJECT] = subject.name
        }
    }

    suspend fun clear() {
        ctx.authDataStore.edit { prefs ->
            prefs.remove(Keys.ACCESS)
            prefs.remove(Keys.REFRESH)
            prefs.remove(Keys.SUBJECT)
        }
    }

    suspend fun access(): String? = accessFlow.first()

    suspend fun refresh(): String? = refreshFlow.first()

    suspend fun subject(): AuthSubject? = subjectFlow.first()

    fun accessBlocking(): String? = kotlinx.coroutines.runBlocking { access() }
}
