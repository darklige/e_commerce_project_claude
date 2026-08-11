package com.jdclone.app.ui.screen.profile

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.ConfirmationNumber
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.ReceiptLong
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material.icons.filled.SupportAgent
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.jdclone.app.data.local.AuthState
import com.jdclone.app.data.local.SessionPrincipal
import com.jdclone.app.ui.common.DangerButton
import com.jdclone.app.ui.common.PrimaryButton
import com.jdclone.app.ui.common.RemoteImage
import com.jdclone.app.ui.common.displayIdentifier

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    onGoLogin: () -> Unit,
    onGoOrders: () -> Unit,
    onGoAftersales: () -> Unit,
    onGoAddresses: () -> Unit,
    onGoNotifications: () -> Unit,
    onGoChangePassword: () -> Unit,
    onGoCoupons: () -> Unit,
    onGoFavorites: () -> Unit,
    onGoFollows: () -> Unit,
    onGoFootprints: () -> Unit,
    vm: ProfileViewModel = hiltViewModel(),
) {
    val authState by vm.authState.collectAsStateWithLifecycle()
    val ui by vm.ui.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(ui.toast) {
        val toast = ui.toast
        if (!toast.isNullOrBlank()) {
            snackbar.showSnackbar(toast)
            vm.clearToast()
        }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("我的") }) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { pad ->
        Column(
            modifier = Modifier.fillMaxSize().padding(pad).verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            when (val s = authState) {
                AuthState.Loading -> Unit
                AuthState.LoggedOut -> LoginCard(onGoLogin = onGoLogin)
                is AuthState.LoggedIn -> when (val principal = s.principal) {
                    is SessionPrincipal.User -> UserCard(
                        displayName = principal.user.nickname,
                        identifier = displayIdentifier(principal.user.phone, principal.user.email),
                    )
                    is SessionPrincipal.Merchant -> UserCard(
                        displayName = principal.shop.name,
                        identifier = principal.account.loginName,
                    )
                }
            }
            MenuGroup(
                items = listOf(
                    MenuItem("我的订单", Icons.Filled.ReceiptLong, onGoOrders),
                    MenuItem("我的售后", Icons.Filled.SupportAgent, onGoAftersales),
                    MenuItem("优惠券中心", Icons.Filled.ConfirmationNumber, onGoCoupons),
                    MenuItem("我的收藏", Icons.Filled.Favorite, onGoFavorites),
                    MenuItem("店铺关注", Icons.Filled.Storefront, onGoFollows),
                    MenuItem("浏览足迹", Icons.Filled.Bookmark, onGoFootprints),
                    MenuItem("地址簿", Icons.Filled.LocationOn, onGoAddresses),
                    MenuItem("通知", Icons.Filled.Notifications, onGoNotifications),
                    MenuItem("修改密码", Icons.Filled.Lock, onGoChangePassword),
                ),
            )
            if (authState is AuthState.LoggedIn) {
                Spacer(Modifier.height(8.dp))
                DangerButton(
                    text = "退出登录",
                    onClick = vm::logout,
                    loading = ui.loading,
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                )
            }
        }
    }
}

@Composable
private fun LoginCard(onGoLogin: () -> Unit) {
    Card {
        Column(modifier = Modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("登录后开启更多功能", style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold))
            Text(
                "浏览订单、售后、活动券、收藏与通知",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
                modifier = Modifier.padding(top = 4.dp, bottom = 16.dp),
            )
            PrimaryButton(text = "去登录", onClick = onGoLogin, modifier = Modifier.fillMaxWidth().height(44.dp))
        }
    }
}

@Composable
private fun UserCard(displayName: String, identifier: String) {
    Card {
        Row(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(color = MaterialTheme.colorScheme.primaryContainer, modifier = Modifier.size(56.dp).clip(CircleShape)) {
                RemoteImage(objectKey = null, modifier = Modifier.fillMaxSize())
            }
            Spacer(Modifier.size(12.dp))
            Column {
                Text(displayName, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold))
                Text(
                    text = identifier,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }
    }
}

private data class MenuItem(val label: String, val icon: ImageVector, val onClick: () -> Unit)

@Composable
private fun MenuGroup(items: List<MenuItem>) {
    Card {
        Column {
            items.forEachIndexed { idx, item ->
                Row(
                    modifier = Modifier.fillMaxWidth().clickable(onClick = item.onClick).padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(item.icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                    Spacer(Modifier.size(12.dp))
                    Text(item.label, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
                    Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = MaterialTheme.colorScheme.outline)
                }
                if (idx != items.lastIndex) HorizontalDivider(modifier = Modifier.padding(start = 52.dp))
            }
        }
    }
}
