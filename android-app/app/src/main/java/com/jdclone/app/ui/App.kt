package com.jdclone.app.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Category
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.ShoppingCart
import androidx.compose.material.icons.outlined.Storefront
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.jdclone.app.data.local.AuthState
import com.jdclone.app.data.local.SessionPrincipal
import com.jdclone.app.data.local.SessionState
import com.jdclone.app.data.repository.AuthRepository
import com.jdclone.app.ui.common.LoadingScreen
import com.jdclone.app.ui.navigation.NavRoutes
import com.jdclone.app.ui.screen.addresses.AddressEditScreen
import com.jdclone.app.ui.screen.addresses.AddressListScreen
import com.jdclone.app.ui.screen.aftersales.AftersalesApplyScreen
import com.jdclone.app.ui.screen.aftersales.AftersalesDetailScreen
import com.jdclone.app.ui.screen.aftersales.AftersalesListScreen
import com.jdclone.app.ui.screen.auth.ForgotPasswordScreen
import com.jdclone.app.ui.screen.auth.LoginScreen
import com.jdclone.app.ui.screen.auth.RegisterScreen
import com.jdclone.app.ui.screen.auth.ResetPasswordScreen
import com.jdclone.app.ui.screen.cart.CartScreen
import com.jdclone.app.ui.screen.catalog.CategoryListScreen
import com.jdclone.app.ui.screen.catalog.CategoryScreen
import com.jdclone.app.ui.screen.catalog.HomeScreen
import com.jdclone.app.ui.screen.catalog.ProductDetailScreen
import com.jdclone.app.ui.screen.catalog.SearchScreen
import com.jdclone.app.ui.screen.catalog.ShopDetailScreen
import com.jdclone.app.ui.screen.checkout.CheckoutScreen
import com.jdclone.app.ui.screen.checkout.MockPaymentScreen
import com.jdclone.app.ui.screen.discovery.ActivityHallScreen
import com.jdclone.app.ui.screen.discovery.CouponCenterScreen
import com.jdclone.app.ui.screen.discovery.FavoritesScreen
import com.jdclone.app.ui.screen.discovery.FollowsScreen
import com.jdclone.app.ui.screen.discovery.FootprintsScreen
import com.jdclone.app.ui.screen.merchant.MerchantAccountScreen
import com.jdclone.app.ui.screen.merchant.MerchantAftersalesScreen
import com.jdclone.app.ui.screen.merchant.MerchantDashboardScreen
import com.jdclone.app.ui.screen.merchant.MerchantDecorationScreen
import com.jdclone.app.ui.screen.merchant.MerchantMessagesScreen
import com.jdclone.app.ui.screen.merchant.MerchantOrdersScreen
import com.jdclone.app.ui.screen.merchant.MerchantProductsScreen
import com.jdclone.app.ui.screen.merchant.MerchantReviewsScreen
import com.jdclone.app.ui.screen.merchant.MerchantShippingScreen
import com.jdclone.app.ui.screen.notifications.NotificationListScreen
import com.jdclone.app.ui.screen.orders.OrderDetailScreen
import com.jdclone.app.ui.screen.orders.OrderListScreen
import com.jdclone.app.ui.screen.profile.ChangePasswordScreen
import com.jdclone.app.ui.screen.profile.ProfileScreen
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AppBootstrapViewModel @Inject constructor(
    private val authRepo: AuthRepository,
    private val session: SessionState,
) : ViewModel() {
    val authState = session.authState

    init {
        viewModelScope.launch { authRepo.bootstrap() }
    }
}

@Composable
fun App(bootstrap: AppBootstrapViewModel = hiltViewModel()) {
    val authState by bootstrap.authState.collectAsStateWithLifecycle()
    when (val state = authState) {
        AuthState.Loading -> LoadingScreen()
        AuthState.LoggedOut -> AuthGraphHost()
        is AuthState.LoggedIn -> when (state.principal) {
            is SessionPrincipal.User -> UserGraphHost()
            is SessionPrincipal.Merchant -> MerchantGraphHost()
        }
    }
}

@Composable
private fun AuthGraphHost() {
    val nav = rememberNavController()
    NavHost(navController = nav, startDestination = NavRoutes.LOGIN) {
        composable(NavRoutes.LOGIN) {
            LoginScreen(
                onLoginSuccess = {},
                onGoRegister = { nav.navigate(NavRoutes.REGISTER) },
                onGoForgot = { nav.navigate(NavRoutes.FORGOT_PASSWORD) },
            )
        }
        composable(NavRoutes.REGISTER) {
            RegisterScreen(onRegistered = {}, onBackToLogin = { nav.popBackStack() })
        }
        composable(NavRoutes.FORGOT_PASSWORD) {
            ForgotPasswordScreen(onDone = { nav.popBackStack() }, onGoReset = { nav.navigate(NavRoutes.RESET_PASSWORD) })
        }
        composable(NavRoutes.RESET_PASSWORD) {
            ResetPasswordScreen(onResetSuccess = { nav.popBackStack(NavRoutes.LOGIN, inclusive = false) })
        }
    }
}

@Composable
private fun UserGraphHost() {
    val nav = rememberNavController()
    val backStackEntry by nav.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val showBottomBar = currentRoute in userBottomTabRoutes

    Scaffold(bottomBar = { if (showBottomBar) BottomBar(nav, userBottomTabs) }) { innerPadding ->
        NavHost(navController = nav, startDestination = NavRoutes.HOME, modifier = Modifier.padding(innerPadding)) {
            composable(NavRoutes.HOME) {
                HomeScreen(
                    onGoSearch = { nav.navigate(NavRoutes.SEARCH) },
                    onGoProduct = { nav.navigate(NavRoutes.productDetail(it)) },
                    onGoCategory = { nav.navigate(NavRoutes.categoryList(it)) },
                    onGoActivityHall = { nav.navigate(NavRoutes.ACTIVITY_HALL) },
                    onGoCouponCenter = { nav.navigate(NavRoutes.COUPON_CENTER) },
                )
            }
            composable(NavRoutes.CATEGORY) {
                CategoryScreen(onGoCategory = { nav.navigate(NavRoutes.categoryList(it)) })
            }
            composable(NavRoutes.CART) {
                CartScreen(
                    onCheckout = { ids -> nav.navigate(NavRoutes.CHECKOUT + "?ids=${ids.joinToString(",")}") },
                    onGoProduct = { nav.navigate(NavRoutes.productDetail(it)) },
                )
            }
            composable(NavRoutes.PROFILE) {
                ProfileScreen(
                    onGoLogin = {},
                    onGoOrders = { nav.navigate(NavRoutes.ORDER_LIST) },
                    onGoAftersales = { nav.navigate(NavRoutes.AFTERSALES_LIST) },
                    onGoAddresses = { nav.navigate(NavRoutes.ADDRESS_LIST) },
                    onGoNotifications = { nav.navigate(NavRoutes.NOTIFICATIONS) },
                    onGoChangePassword = { nav.navigate(NavRoutes.CHANGE_PASSWORD) },
                    onGoCoupons = { nav.navigate(NavRoutes.COUPON_CENTER) },
                    onGoFavorites = { nav.navigate(NavRoutes.FAVORITES) },
                    onGoFollows = { nav.navigate(NavRoutes.FOLLOWS) },
                    onGoFootprints = { nav.navigate(NavRoutes.FOOTPRINTS) },
                )
            }
            composable(NavRoutes.SEARCH) {
                SearchScreen(onBack = { nav.popBackStack() }, onGoProduct = { nav.navigate(NavRoutes.productDetail(it)) })
            }
            composable(NavRoutes.PRODUCT_DETAIL) {
                ProductDetailScreen(
                    onBack = { nav.popBackStack() },
                    onGoCart = { nav.navigate(NavRoutes.CART) },
                    onGoShop = { nav.navigate(NavRoutes.shopDetail(it)) },
                    onGoProduct = { nav.navigate(NavRoutes.productDetail(it)) },
                )
            }
            composable(NavRoutes.CATEGORY_LIST) {
                CategoryListScreen(onBack = { nav.popBackStack() }, onGoProduct = { nav.navigate(NavRoutes.productDetail(it)) })
            }
            composable(NavRoutes.SHOP_DETAIL) {
                ShopDetailScreen(
                    onBack = { nav.popBackStack() },
                    onGoProduct = { nav.navigate(NavRoutes.productDetail(it)) },
                )
            }
            composable(NavRoutes.CHECKOUT + "?ids={ids}") {
                CheckoutScreen(
                    onBack = { nav.popBackStack() },
                    onCreated = { orderId ->
                        nav.navigate(NavRoutes.mockPayment(sessionId = 0L, orderId = orderId)) {
                            popUpTo(NavRoutes.CART)
                        }
                    },
                )
            }
            composable(NavRoutes.MOCK_PAYMENT) {
                MockPaymentScreen(
                    onPaid = { orderId ->
                        nav.navigate(NavRoutes.orderDetail(orderId)) { popUpTo(NavRoutes.CART) }
                    },
                    onCancel = { nav.popBackStack() },
                )
            }
            composable(NavRoutes.ORDER_LIST) {
                OrderListScreen(
                    onBack = { nav.popBackStack() },
                    onOpenOrder = { nav.navigate(NavRoutes.orderDetail(it)) },
                    onPayOrder = { nav.navigate(NavRoutes.mockPayment(sessionId = 0L, orderId = it)) },
                )
            }
            composable(NavRoutes.ORDER_DETAIL) {
                OrderDetailScreen(
                    onBack = { nav.popBackStack() },
                    onPay = { nav.navigate(NavRoutes.mockPayment(sessionId = 0L, orderId = it)) },
                    onAftersalesApply = { nav.navigate(NavRoutes.aftersalesApply(it)) },
                )
            }
            composable(NavRoutes.AFTERSALES_APPLY) {
                AftersalesApplyScreen(
                    onBack = { nav.popBackStack() },
                    onSubmitted = { asId ->
                        nav.navigate(NavRoutes.aftersalesDetail(asId)) { popUpTo(NavRoutes.ORDER_LIST) }
                    },
                )
            }
            composable(NavRoutes.AFTERSALES_LIST) {
                AftersalesListScreen(onBack = { nav.popBackStack() }, onOpen = { nav.navigate(NavRoutes.aftersalesDetail(it)) })
            }
            composable(NavRoutes.AFTERSALES_DETAIL) {
                AftersalesDetailScreen(onBack = { nav.popBackStack() })
            }
            composable(NavRoutes.ADDRESS_LIST) {
                AddressListScreen(onBack = { nav.popBackStack() }, onAdd = { nav.navigate(NavRoutes.addressEdit(null)) }, onEdit = { nav.navigate(NavRoutes.addressEdit(it)) })
            }
            composable(NavRoutes.ADDRESS_EDIT) {
                AddressEditScreen(onBack = { nav.popBackStack() }, onSaved = { nav.popBackStack() })
            }
            composable(NavRoutes.NOTIFICATIONS) {
                NotificationListScreen(
                    onBack = { nav.popBackStack() },
                    onOpenAction = { notif ->
                        when (notif.relatedType) {
                            "order" -> notif.relatedId?.let { nav.navigate(NavRoutes.orderDetail(it)) }
                            "aftersales" -> notif.relatedId?.let { nav.navigate(NavRoutes.aftersalesDetail(it)) }
                        }
                    },
                )
            }
            composable(NavRoutes.CHANGE_PASSWORD) {
                ChangePasswordScreen(onBack = { nav.popBackStack() })
            }
            composable(NavRoutes.ACTIVITY_HALL) {
                ActivityHallScreen(onBack = { nav.popBackStack() }, onOpenCoupons = { nav.navigate(NavRoutes.COUPON_CENTER) }, onOpenProduct = { nav.navigate(NavRoutes.productDetail(it)) })
            }
            composable(NavRoutes.COUPON_CENTER) {
                CouponCenterScreen(onBack = { nav.popBackStack() })
            }
            composable(NavRoutes.FAVORITES) {
                FavoritesScreen(onBack = { nav.popBackStack() }, onOpenProduct = { nav.navigate(NavRoutes.productDetail(it)) })
            }
            composable(NavRoutes.FOLLOWS) {
                FollowsScreen(onBack = { nav.popBackStack() })
            }
            composable(NavRoutes.FOOTPRINTS) {
                FootprintsScreen(onBack = { nav.popBackStack() }, onOpenProduct = { nav.navigate(NavRoutes.productDetail(it)) })
            }
        }
    }
}

@Composable
private fun MerchantGraphHost() {
    val nav = rememberNavController()
    val backStackEntry by nav.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val showBottomBar = currentRoute in merchantBottomTabRoutes

    Scaffold(bottomBar = { if (showBottomBar) BottomBar(nav, merchantBottomTabs) }) { innerPadding ->
        NavHost(navController = nav, startDestination = NavRoutes.MERCHANT_DASHBOARD, modifier = Modifier.padding(innerPadding)) {
            composable(NavRoutes.MERCHANT_DASHBOARD) {
                MerchantDashboardScreen(
                    onGoProducts = { nav.navigate(NavRoutes.MERCHANT_PRODUCTS) },
                    onGoShipping = { nav.navigate(NavRoutes.MERCHANT_SHIPPING) },
                    onGoMessages = { nav.navigate(NavRoutes.MERCHANT_MESSAGES) },
                    onGoReviews = { nav.navigate(NavRoutes.MERCHANT_REVIEWS) },
                    onGoDecoration = { nav.navigate(NavRoutes.MERCHANT_DECORATION) },
                    onGoOrders = { nav.navigate(NavRoutes.MERCHANT_ORDERS) },
                    onGoAftersales = { nav.navigate(NavRoutes.MERCHANT_AFTERSALES) },
                )
            }
            composable(NavRoutes.MERCHANT_PRODUCTS) { MerchantProductsScreen() }
            composable(NavRoutes.MERCHANT_ORDERS) { MerchantOrdersScreen() }
            composable(NavRoutes.MERCHANT_AFTERSALES) { MerchantAftersalesScreen() }
            composable(NavRoutes.MERCHANT_ACCOUNT) { MerchantAccountScreen(onGoDecoration = { nav.navigate(NavRoutes.MERCHANT_DECORATION) }) }
            composable(NavRoutes.MERCHANT_SHIPPING) { MerchantShippingScreen() }
            composable(NavRoutes.MERCHANT_MESSAGES) { MerchantMessagesScreen() }
            composable(NavRoutes.MERCHANT_REVIEWS) { MerchantReviewsScreen() }
            composable(NavRoutes.MERCHANT_DECORATION) { MerchantDecorationScreen() }
        }
    }
}

private data class BottomTab(val route: String, val label: String, val icon: ImageVector)

private val userBottomTabRoutes = setOf(NavRoutes.HOME, NavRoutes.CATEGORY, NavRoutes.CART, NavRoutes.PROFILE)
private val merchantBottomTabRoutes = setOf(NavRoutes.MERCHANT_DASHBOARD, NavRoutes.MERCHANT_PRODUCTS, NavRoutes.MERCHANT_ORDERS, NavRoutes.MERCHANT_ACCOUNT)

private val userBottomTabs = listOf(
    BottomTab(NavRoutes.HOME, "首页", Icons.Outlined.Home),
    BottomTab(NavRoutes.CATEGORY, "分类", Icons.Outlined.Category),
    BottomTab(NavRoutes.CART, "购物车", Icons.Outlined.ShoppingCart),
    BottomTab(NavRoutes.PROFILE, "我的", Icons.Outlined.Person),
)

private val merchantBottomTabs = listOf(
    BottomTab(NavRoutes.MERCHANT_DASHBOARD, "工作台", Icons.Outlined.Storefront),
    BottomTab(NavRoutes.MERCHANT_PRODUCTS, "商品", Icons.Outlined.Category),
    BottomTab(NavRoutes.MERCHANT_ORDERS, "订单", Icons.Outlined.ShoppingCart),
    BottomTab(NavRoutes.MERCHANT_ACCOUNT, "账号", Icons.Outlined.Person),
)

@Composable
private fun BottomBar(nav: NavHostController, tabs: List<BottomTab>) {
    val backStackEntry by nav.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    NavigationBar {
        tabs.forEach { tab ->
            NavigationBarItem(
                selected = backStackEntry?.destination?.hierarchy?.any { it.route == tab.route } == true,
                onClick = {
                    if (currentRoute != tab.route) {
                        nav.navigate(tab.route) {
                            popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                },
                icon = { Icon(tab.icon, contentDescription = tab.label) },
                label = { Text(tab.label) },
            )
        }
    }
}
