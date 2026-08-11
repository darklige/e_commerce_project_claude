package com.jdclone.app.ui.screen.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.jdclone.app.data.repository.AuthRepository
import com.jdclone.app.data.repository.MerchantRepository
import com.jdclone.app.ui.common.UiState
import com.jdclone.app.ui.common.errorMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

enum class LoginMode {
    USER,
    MERCHANT,
}

sealed interface AuthEffect {
    data object LoginSuccess : AuthEffect
    data object RegisterSuccess : AuthEffect
    data class Info(val message: String) : AuthEffect
}

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val repo: AuthRepository,
    private val merchantRepo: MerchantRepository,
) : ViewModel() {

    private val _mutation = MutableStateFlow<UiState<Unit>>(UiState.Success(Unit))
    val mutation: StateFlow<UiState<Unit>> = _mutation.asStateFlow()

    private val _effect = MutableStateFlow<AuthEffect?>(null)
    val effect: StateFlow<AuthEffect?> = _effect.asStateFlow()

    fun clearEffect() {
        _effect.value = null
    }

    fun clearMutation() {
        _mutation.value = UiState.Success(Unit)
    }

    fun login(identifier: String, password: String, mode: LoginMode) {
        if (identifier.isBlank() || password.isBlank()) {
            _mutation.value = UiState.Error("请输入账号和密码")
            return
        }
        _mutation.value = UiState.Loading
        viewModelScope.launch {
            val result = when (mode) {
                LoginMode.USER -> repo.login(identifier.trim(), password).map { Unit }
                LoginMode.MERCHANT -> merchantRepo.login(identifier.trim(), password).map { Unit }
            }
            _mutation.value = result.fold(
                onSuccess = { UiState.Success(Unit) },
                onFailure = { UiState.Error(errorMessage(it)) },
            )
            if (result.isSuccess) _effect.value = AuthEffect.LoginSuccess
        }
    }

    fun register(
        phone: String?,
        email: String?,
        password: String,
        confirmPassword: String,
        nickname: String?,
    ) {
        val phoneOk = !phone.isNullOrBlank()
        val emailOk = !email.isNullOrBlank()
        if (!phoneOk && !emailOk) {
            _mutation.value = UiState.Error("请填写手机号或邮箱")
            return
        }
        if (password.length < 8) {
            _mutation.value = UiState.Error("密码至少 8 位")
            return
        }
        if (password != confirmPassword) {
            _mutation.value = UiState.Error("两次密码不一致")
            return
        }
        _mutation.value = UiState.Loading
        viewModelScope.launch {
            val r = repo.register(phone, email, password, nickname)
            _mutation.value = r.fold(
                onSuccess = { UiState.Success(Unit) },
                onFailure = { UiState.Error(errorMessage(it)) },
            )
            if (r.isSuccess) _effect.value = AuthEffect.RegisterSuccess
        }
    }

    fun forgotPassword(identifier: String) {
        if (identifier.isBlank()) {
            _mutation.value = UiState.Error("请填写账号")
            return
        }
        _mutation.value = UiState.Loading
        viewModelScope.launch {
            val r = repo.forgotPassword(identifier.trim())
            _mutation.value = r.fold(
                onSuccess = { UiState.Success(Unit) },
                onFailure = { UiState.Error(errorMessage(it)) },
            )
            if (r.isSuccess) _effect.value = AuthEffect.Info("验证码已发送，请查看后端日志")
        }
    }

    fun resetPassword(identifier: String, code: String, newPassword: String) {
        if (identifier.isBlank() || code.isBlank() || newPassword.length < 8) {
            _mutation.value = UiState.Error("请填写完整信息（密码至少 8 位）")
            return
        }
        _mutation.value = UiState.Loading
        viewModelScope.launch {
            val r = repo.resetPassword(identifier.trim(), code.trim(), newPassword)
            _mutation.value = r.fold(
                onSuccess = { UiState.Success(Unit) },
                onFailure = { UiState.Error(errorMessage(it)) },
            )
            if (r.isSuccess) _effect.value = AuthEffect.Info("密码已重置，请重新登录")
        }
    }
}
