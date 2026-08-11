package com.jdclone.app.ui.navigation

object NavRoutes {
    const val LOGIN = "auth/login"
    const val REGISTER = "auth/register"
    const val FORGOT_PASSWORD = "auth/forgot"
    const val RESET_PASSWORD = "auth/reset"

    const val HOME = "main/home"
    const val CATEGORY = "main/category"
    const val CART = "main/cart"
    const val PROFILE = "main/profile"

    const val SEARCH = "catalog/search"
    const val PRODUCT_DETAIL = "catalog/product/{id}"
    fun productDetail(id: Long): String = "catalog/product/$id"
    const val CATEGORY_LIST = "catalog/category/{id}"
    fun categoryList(id: Long): String = "catalog/category/$id"

    const val SHOP_DETAIL = "shops/{id}"
    fun shopDetail(id: Long): String = "shops/$id"

    const val CHECKOUT = "checkout"
    const val MOCK_PAYMENT = "checkout/pay/{sessionId}?orderId={orderId}"
    fun mockPayment(sessionId: Long, orderId: Long): String = "checkout/pay/$sessionId?orderId=$orderId"

    const val ORDER_LIST = "orders"
    const val ORDER_DETAIL = "orders/{orderId}"
    fun orderDetail(orderId: Long): String = "orders/$orderId"

    const val AFTERSALES_APPLY = "aftersales/apply/{orderId}"
    fun aftersalesApply(orderId: Long): String = "aftersales/apply/$orderId"
    const val AFTERSALES_LIST = "aftersales"
    const val AFTERSALES_DETAIL = "aftersales/{id}"
    fun aftersalesDetail(id: Long): String = "aftersales/$id"

    const val ADDRESS_LIST = "addresses"
    const val ADDRESS_EDIT = "addresses/edit?id={id}"
    fun addressEdit(id: Long? = null): String = "addresses/edit?id=${id ?: 0}"

    const val NOTIFICATIONS = "notifications"
    const val CHANGE_PASSWORD = "profile/change-password"

    const val ACTIVITY_HALL = "engagement/activity"
    const val COUPON_CENTER = "engagement/coupons"
    const val FAVORITES = "engagement/favorites"
    const val FOLLOWS = "engagement/follows"
    const val FOOTPRINTS = "engagement/footprints"

    const val MERCHANT_DASHBOARD = "merchant/dashboard"
    const val MERCHANT_PRODUCTS = "merchant/products"
    const val MERCHANT_ORDERS = "merchant/orders"
    const val MERCHANT_AFTERSALES = "merchant/aftersales"
    const val MERCHANT_ACCOUNT = "merchant/account"
    const val MERCHANT_SHIPPING = "merchant/shipping"
    const val MERCHANT_MESSAGES = "merchant/messages"
    const val MERCHANT_REVIEWS = "merchant/reviews"
    const val MERCHANT_DECORATION = "merchant/decoration"
}
