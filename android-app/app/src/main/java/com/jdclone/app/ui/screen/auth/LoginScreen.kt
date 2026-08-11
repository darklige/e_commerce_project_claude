package com.jdclone.app.ui.screen.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.jdclone.app.ui.common.PrimaryButton
import com.jdclone.app.ui.common.SecondaryButton
import com.jdclone.app.ui.common.UiState

@Composable
fun LoginScreen(
    onLoginSuccess: () -> Unit,
    onGoRegister: () -> Unit,
    onGoForgot: () -> Unit,
    vm: AuthViewModel = hiltViewModel(),
) {
    var mode by rememberSaveable { mutableStateOf(LoginMode.USER) }
    var identifier by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }

    val mutation by vm.mutation.collectAsStateWithLifecycle()
    val effect by vm.effect.collectAsStateWithLifecycle()

    LaunchedEffect(effect) {
        if (effect is AuthEffect.LoginSuccess) {
            vm.clearEffect()
            onLoginSuccess()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp)
            .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "JD Clone",
            style = MaterialTheme.typography.displaySmall.copy(fontWeight = FontWeight.Bold),
            color = MaterialTheme.colorScheme.primary,
        )
        Text(
            text = if (mode == LoginMode.USER) "登录用户端，继续下单与支付" else "登录商家端，查看订单与售后",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.outline,
            modifier = Modifier.padding(top = 8.dp, bottom = 24.dp),
        )

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    shape = RoundedCornerShape(16.dp),
                )
                .padding(4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            SecondaryButton(
                text = "用户登录",
                onClick = { mode = LoginMode.USER },
                modifier = Modifier.weight(1f),
                enabled = mode != LoginMode.USER,
            )
            SecondaryButton(
                text = "商家登录",
                onClick = { mode = LoginMode.MERCHANT },
                modifier = Modifier.weight(1f),
                enabled = mode != LoginMode.MERCHANT,
            )
        }

        Spacer(Modifier.height(20.dp))
        OutlinedTextField(
            value = identifier,
            onValueChange = { identifier = it },
            label = { Text(if (mode == LoginMode.USER) "手机号或邮箱" else "商家登录名") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(
                keyboardType = if (mode == LoginMode.USER) KeyboardType.Email else KeyboardType.Text,
            ),
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(12.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("密码") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth(),
        )
        if (mutation is UiState.Error) {
            Text(
                text = (mutation as UiState.Error).message,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
            )
        }
        Spacer(Modifier.height(20.dp))
        PrimaryButton(
            text = if (mode == LoginMode.USER) "登录用户端" else "登录商家端",
            onClick = { vm.login(identifier, password, mode) },
            loading = mutation is UiState.Loading,
            modifier = Modifier.fillMaxWidth().height(48.dp),
        )
        if (mode == LoginMode.USER) {
            Spacer(Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                TextButton(onClick = onGoForgot) { Text("忘记密码") }
                TextButton(onClick = onGoRegister) { Text("去注册") }
            }
        } else {
            Text(
                text = "演示商家账号可使用 seed 数据中的 shop1_owner / Merch1234",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
                modifier = Modifier.padding(top = 12.dp),
            )
        }
    }
}
