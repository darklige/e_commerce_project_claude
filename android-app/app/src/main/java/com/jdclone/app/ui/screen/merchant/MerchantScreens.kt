package com.jdclone.app.ui.screen.merchant

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.jdclone.app.data.local.SessionState
import com.jdclone.app.data.network.PageData
import com.jdclone.app.data.network.dto.AftersalesDetailDto
import com.jdclone.app.data.network.dto.AftersalesListItemDto
import com.jdclone.app.data.network.dto.InventoryLogDto
import com.jdclone.app.data.network.dto.MerchantMeDto
import com.jdclone.app.data.network.dto.MerchantReviewDto
import com.jdclone.app.data.network.dto.NotificationDto
import com.jdclone.app.data.network.dto.OrderListItemDto
import com.jdclone.app.data.network.dto.SkuDto
import com.jdclone.app.data.network.dto.SpuDetailDto
import com.jdclone.app.data.network.dto.SpuListItemDto
import com.jdclone.app.data.repository.AuthRepository
import com.jdclone.app.data.repository.MerchantRepository
import com.jdclone.app.ui.common.DangerButton
import com.jdclone.app.ui.common.EmptyState
import com.jdclone.app.ui.common.ErrorScreen
import com.jdclone.app.ui.common.LoadingScreen
import com.jdclone.app.ui.common.PriceText
import com.jdclone.app.ui.common.UiState
import com.jdclone.app.ui.common.errorMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

private fun orderStatusLabel(status: String): String = when (status) {
    "pending_payment" -> "待付款"
    "paid" -> "待发货"
    "shipped" -> "已发货"
    "completed" -> "已完成"
    "cancelled" -> "已取消"
    else -> status
}

private fun aftersalesStatusLabel(status: String): String = when (status) {
    "pending_merchant_review" -> "待审核"
    "merchant_agreed_waiting_return" -> "待买家寄回"
    "return_shipped_waiting_receive" -> "待收货"
    "merchant_agreed_waiting_ship" -> "待补发"
    "completed" -> "已完成"
    "merchant_rejected" -> "已驳回"
    else -> status
}

private fun aftersalesActionHint(status: String): String = when (status) {
    "pending_merchant_review" -> "可同意或驳回当前售后申请"
    "return_shipped_waiting_receive" -> "买家已寄回商品，可确认收货或拒收"
    "merchant_agreed_waiting_ship" -> "售后已通过，等待商家补发换货"
    else -> "可记录工单备注并查看流转历史"
}

private fun parseIntOrZero(value: String): Int = value.trim().toIntOrNull() ?: 0
private fun parseLongOrNull(value: String): Long? = value.trim().toLongOrNull()

data class MerchantDashboardUiState(
    val state: UiState<Pair<Int, Int>> = UiState.Loading,
)

@HiltViewModel
class MerchantDashboardViewModel @Inject constructor(
    private val repo: MerchantRepository,
) : ViewModel() {
    private val _ui = MutableStateFlow(MerchantDashboardUiState())
    val ui: StateFlow<MerchantDashboardUiState> = _ui.asStateFlow()

    fun load() {
        viewModelScope.launch {
            val orders = repo.getOrderStats()
            val aftersales = repo.getAftersalesStats()
            _ui.value = if (orders.isSuccess && aftersales.isSuccess) {
                val orderStats = orders.getOrThrow()
                val aftersalesStats = aftersales.getOrThrow()
                MerchantDashboardUiState(
                    UiState.Success(orderStats.paidPendingShipCount to aftersalesStats.pendingReviewCount),
                )
            } else {
                MerchantDashboardUiState(
                    UiState.Error(errorMessage(orders.exceptionOrNull() ?: aftersales.exceptionOrNull()!!)),
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MerchantDashboardScreen(
    onGoProducts: () -> Unit,
    onGoShipping: () -> Unit,
    onGoMessages: () -> Unit,
    onGoReviews: () -> Unit,
    onGoDecoration: () -> Unit,
    onGoOrders: () -> Unit,
    onGoAftersales: () -> Unit,
    vm: MerchantDashboardViewModel = hiltViewModel(),
) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { vm.load() }
    Scaffold(topBar = { TopAppBar(title = { Text("商家工作台") }) }) { pad ->
        when (val state = ui.state) {
            UiState.Loading -> LoadingScreen(Modifier.padding(pad))
            is UiState.Error -> ErrorScreen(state.message, vm::load, Modifier.padding(pad))
            is UiState.Success -> {
                val (pendingShip, pendingReview) = state.data
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(pad),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item {
                        Card {
                            Column(
                                Modifier.fillMaxWidth().padding(16.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                Text("今日提醒", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                Text("待发货订单 $pendingShip 单")
                                Text("待处理售后 $pendingReview 单")
                            }
                        }
                    }
                    items(
                        listOf(
                            "商品管理" to onGoProducts,
                            "发货面板" to onGoShipping,
                            "消息中心" to onGoMessages,
                            "评价回复" to onGoReviews,
                            "店铺装修" to onGoDecoration,
                            "订单列表" to onGoOrders,
                            "售后工单" to onGoAftersales,
                        ),
                    ) { entry ->
                        ActionCard(entry.first, entry.second)
                    }
                }
            }
        }
    }
}

@Composable
private fun ActionCard(title: String, onClick: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text("进入", color = MaterialTheme.colorScheme.primary)
        }
    }
}

data class MerchantOrdersUiState(
    val state: UiState<PageData<OrderListItemDto>> = UiState.Loading,
    val keyword: String = "",
    val busyOrderId: Long? = null,
    val toast: String? = null,
)

@HiltViewModel
class MerchantOrdersViewModel @Inject constructor(private val repo: MerchantRepository) : ViewModel() {
    private val _ui = MutableStateFlow(MerchantOrdersUiState())
    val ui: StateFlow<MerchantOrdersUiState> = _ui.asStateFlow()

    fun load(keyword: String = _ui.value.keyword) {
        _ui.value = _ui.value.copy(keyword = keyword)
        viewModelScope.launch {
            val result = repo.listOrders(keyword = keyword.ifBlank { null })
            _ui.value = _ui.value.copy(
                state = result.fold(
                    onSuccess = { UiState.Success(it) },
                    onFailure = { UiState.Error(errorMessage(it)) },
                ),
            )
        }
    }

    fun cancel(orderId: Long, cancelNote: String) {
        _ui.value = _ui.value.copy(busyOrderId = orderId)
        viewModelScope.launch {
            repo.cancelOrder(orderId, cancelNote).fold(
                onSuccess = {
                    _ui.value = _ui.value.copy(busyOrderId = null, toast = "订单已取消")
                    load()
                },
                onFailure = {
                    _ui.value = _ui.value.copy(busyOrderId = null, toast = errorMessage(it))
                },
            )
        }
    }

    fun clearToast() {
        _ui.value = _ui.value.copy(toast = null)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MerchantOrdersScreen(vm: MerchantOrdersViewModel = hiltViewModel()) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    var search by rememberSaveable { mutableStateOf("") }
    LaunchedEffect(Unit) { vm.load() }
    LaunchedEffect(ui.toast) {
        ui.toast?.let {
            snackbar.showSnackbar(it)
            vm.clearToast()
        }
    }
    Scaffold(
        topBar = { TopAppBar(title = { Text("商家订单") }) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { pad ->
        when (val state = ui.state) {
            UiState.Loading -> LoadingScreen(Modifier.padding(pad))
            is UiState.Error -> ErrorScreen(state.message, { vm.load(search) }, Modifier.padding(pad))
            is UiState.Success -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(pad),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            OutlinedTextField(
                                value = search,
                                onValueChange = { search = it },
                                modifier = Modifier.weight(1f),
                                label = { Text("查找订单号/收货人") },
                            )
                            Button(onClick = { vm.load(search) }) { Text("查找") }
                        }
                    }
                    if (state.data.items.isEmpty()) {
                        item { EmptyState("暂无订单") }
                    } else {
                        items(state.data.items) { order ->
                            var cancelNote by remember(order.id) { mutableStateOf("商家侧取消订单，用于演示删除流程") }
                            Card {
                                Column(
                                    Modifier.fillMaxWidth().padding(16.dp),
                                    verticalArrangement = Arrangement.spacedBy(8.dp),
                                ) {
                                    Text(order.orderNo, fontWeight = FontWeight.SemiBold)
                                    Text(orderStatusLabel(order.status), color = MaterialTheme.colorScheme.primary)
                                    Text("收货人：${order.receiverName}")
                                    PriceText(order.totalCents)
                                    OutlinedTextField(
                                        value = cancelNote,
                                        onValueChange = { cancelNote = it },
                                        modifier = Modifier.fillMaxWidth(),
                                        label = { Text("删除/取消备注") },
                                    )
                                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                        TextButton(onClick = { vm.load(order.orderNo) }) {
                                            Text("查找同单号")
                                        }
                                        OutlinedButton(
                                            onClick = { vm.cancel(order.id, cancelNote) },
                                            enabled = order.status == "paid" && ui.busyOrderId != order.id && cancelNote.isNotBlank(),
                                        ) {
                                            Text(if (ui.busyOrderId == order.id) "处理中..." else "删除订单")
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

data class MerchantAftersalesUiState(
    val state: UiState<PageData<AftersalesListItemDto>> = UiState.Loading,
    val selectedDetail: AftersalesDetailDto? = null,
    val busy: Boolean = false,
    val toast: String? = null,
)

@HiltViewModel
class MerchantAftersalesViewModel @Inject constructor(private val repo: MerchantRepository) : ViewModel() {
    private val _ui = MutableStateFlow(MerchantAftersalesUiState())
    val ui: StateFlow<MerchantAftersalesUiState> = _ui.asStateFlow()

    fun load() {
        viewModelScope.launch {
            val result = repo.listAftersales()
            _ui.value = _ui.value.copy(
                state = result.fold(
                    onSuccess = { UiState.Success(it) },
                    onFailure = { UiState.Error(errorMessage(it)) },
                ),
            )
        }
    }

    fun select(id: Long) {
        viewModelScope.launch {
            repo.getAftersales(id).fold(
                onSuccess = { _ui.value = _ui.value.copy(selectedDetail = it) },
                onFailure = { _ui.value = _ui.value.copy(toast = errorMessage(it)) },
            )
        }
    }

    fun approve(id: Long, actualRefundCents: Int, returnAddress: String, reviewNote: String) {
        handleWorkflow {
            repo.approveAftersales(id, actualRefundCents, returnAddress, reviewNote)
        }
    }

    fun reject(id: Long, reviewNote: String) {
        handleWorkflow { repo.rejectAftersales(id, reviewNote) }
    }

    fun confirmReceived(id: Long, note: String) {
        handleWorkflow { repo.confirmAftersalesReceived(id, note) }
    }

    fun refuseReceive(id: Long, note: String) {
        handleWorkflow { repo.refuseAftersalesReceive(id, note) }
    }

    fun shipExchange(id: Long, carrier: String, trackingNo: String) {
        handleWorkflow { repo.shipAftersalesExchange(id, carrier, trackingNo) }
    }

    fun note(id: Long, note: String) {
        handleWorkflow { repo.noteAftersales(id, note) }
    }

    fun clearToast() {
        _ui.value = _ui.value.copy(toast = null)
    }

    private fun handleWorkflow(block: suspend () -> Result<AftersalesDetailDto>) {
        _ui.value = _ui.value.copy(busy = true)
        viewModelScope.launch {
            block().fold(
                onSuccess = {
                    _ui.value = _ui.value.copy(
                        selectedDetail = it,
                        busy = false,
                        toast = "售后工单已更新",
                    )
                    load()
                },
                onFailure = {
                    _ui.value = _ui.value.copy(busy = false, toast = errorMessage(it))
                },
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MerchantAftersalesScreen(vm: MerchantAftersalesViewModel = hiltViewModel()) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(Unit) { vm.load() }
    LaunchedEffect(ui.toast) {
        ui.toast?.let {
            snackbar.showSnackbar(it)
            vm.clearToast()
        }
    }
    Scaffold(
        topBar = { TopAppBar(title = { Text("售后工单") }) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { pad ->
        when (val state = ui.state) {
            UiState.Loading -> LoadingScreen(Modifier.padding(pad))
            is UiState.Error -> ErrorScreen(state.message, vm::load, Modifier.padding(pad))
            is UiState.Success -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(pad),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    if (state.data.items.isEmpty()) {
                        item { EmptyState("暂无售后工单") }
                    } else {
                        items(state.data.items) { aftersales ->
                            Card(modifier = Modifier.clickable { vm.select(aftersales.id) }) {
                                Column(
                                    Modifier.fillMaxWidth().padding(16.dp),
                                    verticalArrangement = Arrangement.spacedBy(6.dp),
                                ) {
                                    Text(aftersales.aftersalesNo, fontWeight = FontWeight.SemiBold)
                                    Text(aftersalesStatusLabel(aftersales.status), color = MaterialTheme.colorScheme.primary)
                                    Text("类型：${aftersales.type}")
                                    Text(aftersalesActionHint(aftersales.status), color = MaterialTheme.colorScheme.outline)
                                    PriceText(aftersales.refundAmountCents)
                                }
                            }
                        }
                    }
                    ui.selectedDetail?.let { detail ->
                        item {
                            AftersalesWorkflowCard(
                                detail = detail,
                                busy = ui.busy,
                                onApprove = vm::approve,
                                onReject = vm::reject,
                                onConfirmReceived = vm::confirmReceived,
                                onRefuseReceive = vm::refuseReceive,
                                onShipExchange = vm::shipExchange,
                                onNote = vm::note,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AftersalesWorkflowCard(
    detail: AftersalesDetailDto,
    busy: Boolean,
    onApprove: (Long, Int, String, String) -> Unit,
    onReject: (Long, String) -> Unit,
    onConfirmReceived: (Long, String) -> Unit,
    onRefuseReceive: (Long, String) -> Unit,
    onShipExchange: (Long, String, String) -> Unit,
    onNote: (Long, String) -> Unit,
) {
    var actualRefund by remember(detail.id, detail.actualRefundCents) {
        mutableStateOf((detail.actualRefundCents ?: detail.refundAmountCents).toString())
    }
    var returnAddress by remember(detail.id) { mutableStateOf(detail.returnAddress.orEmpty()) }
    var reviewNote by remember(detail.id) { mutableStateOf(detail.merchantReviewNote.orEmpty()) }
    var note by remember(detail.id) { mutableStateOf(detail.merchantReviewNote.orEmpty()) }
    var carrier by remember(detail.id) { mutableStateOf(detail.exchangeCarrier ?: "JD-Express") }
    var trackingNo by remember(detail.id) { mutableStateOf(detail.exchangeTrackingNo.orEmpty()) }
    Card {
        Column(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("工单处理台", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                if (busy) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                }
            }
            Text("工单号：${detail.aftersalesNo}")
            Text("当前状态：${aftersalesStatusLabel(detail.status)}")
            Text("售后原因：${detail.reasonNote}")
            Text("状态轨迹：${detail.statusHistory.takeLast(3).joinToString(" -> ") { it.toStatus }}")
            OutlinedTextField(
                value = note,
                onValueChange = { note = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("工单备注") },
            )
            when (detail.status) {
                "pending_merchant_review" -> {
                    OutlinedTextField(
                        value = actualRefund,
                        onValueChange = { actualRefund = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("实际退款金额（分）") },
                    )
                    OutlinedTextField(
                        value = returnAddress,
                        onValueChange = { returnAddress = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("退货地址") },
                    )
                    OutlinedTextField(
                        value = reviewNote,
                        onValueChange = { reviewNote = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("审核备注") },
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick = { onApprove(detail.id, parseIntOrZero(actualRefund), returnAddress, reviewNote) },
                            enabled = !busy,
                        ) {
                            Text("同意售后")
                        }
                        OutlinedButton(
                            onClick = { onReject(detail.id, reviewNote.ifBlank { "售后信息不足，请补充后重试" }) },
                            enabled = !busy && reviewNote.trim().length >= 5,
                        ) {
                            Text("驳回申请")
                        }
                    }
                }
                "return_shipped_waiting_receive" -> {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { onConfirmReceived(detail.id, note) }, enabled = !busy) {
                            Text("确认收货")
                        }
                        OutlinedButton(
                            onClick = { onRefuseReceive(detail.id, note.ifBlank { "商品退回异常，已拒收并升级处理" }) },
                            enabled = !busy && note.trim().length >= 10,
                        ) {
                            Text("拒收退货")
                        }
                    }
                }
                "merchant_agreed_waiting_ship" -> {
                    OutlinedTextField(
                        value = carrier,
                        onValueChange = { carrier = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("换货物流") },
                    )
                    OutlinedTextField(
                        value = trackingNo,
                        onValueChange = { trackingNo = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("换货单号") },
                    )
                    Button(
                        onClick = { onShipExchange(detail.id, carrier.ifBlank { "JD-Express" }, trackingNo) },
                        enabled = !busy && trackingNo.trim().length >= 4,
                    ) {
                        Text("提交补发")
                    }
                }
            }
            OutlinedButton(onClick = { onNote(detail.id, note.ifBlank { "已跟进处理" }) }, enabled = !busy) {
                Text("保存备注")
            }
        }
    }
}

data class MerchantProductsUiState(
    val state: UiState<PageData<SpuListItemDto>> = UiState.Loading,
    val keyword: String = "",
    val selectedSpu: SpuDetailDto? = null,
    val logs: List<InventoryLogDto> = emptyList(),
    val busy: Boolean = false,
    val toast: String? = null,
)

@HiltViewModel
class MerchantProductsViewModel @Inject constructor(private val repo: MerchantRepository) : ViewModel() {
    private val _ui = MutableStateFlow(MerchantProductsUiState())
    val ui: StateFlow<MerchantProductsUiState> = _ui.asStateFlow()

    fun load(keyword: String = _ui.value.keyword) {
        _ui.value = _ui.value.copy(keyword = keyword)
        viewModelScope.launch {
            val result = repo.listSpus(keyword = keyword.ifBlank { null })
            _ui.value = _ui.value.copy(
                state = result.fold(
                    onSuccess = { UiState.Success(it) },
                    onFailure = { UiState.Error(errorMessage(it)) },
                ),
            )
        }
    }

    fun select(spuId: Long) {
        viewModelScope.launch {
            val detail = repo.getSpu(spuId).getOrNull() ?: return@launch
            val logs = detail.skus.firstOrNull()?.let { sku ->
                repo.listInventoryLogs(sku.id).getOrNull()?.items ?: emptyList()
            } ?: emptyList()
            _ui.value = _ui.value.copy(selectedSpu = detail, logs = logs)
        }
    }

    fun createSpu(
        categoryId: Long,
        brandId: Long?,
        title: String,
        subtitle: String,
        description: String,
        mainImage: String,
    ) {
        executeProductAction("商品已创建") {
            repo.createSpu(categoryId, brandId, title, subtitle, description, mainImage)
        }
    }

    fun updateSpu(
        id: Long,
        categoryId: Long,
        brandId: Long?,
        title: String,
        subtitle: String,
        description: String,
        mainImage: String,
    ) {
        executeProductAction("商品信息已更新") {
            repo.updateSpu(id, categoryId, brandId, title, subtitle, description, mainImage)
        }
    }

    fun deleteSpu(id: Long) {
        _ui.value = _ui.value.copy(busy = true)
        viewModelScope.launch {
            repo.deleteSpu(id).fold(
                onSuccess = {
                    _ui.value = _ui.value.copy(selectedSpu = null, busy = false, toast = "商品已删除")
                    load()
                },
                onFailure = { _ui.value = _ui.value.copy(busy = false, toast = errorMessage(it)) },
            )
        }
    }

    fun changeStatus(spuId: Long, status: String) {
        executeProductAction("商品状态已更新") {
            when (status) {
                "draft" -> repo.submitReview(spuId)
                "pending_review" -> repo.withdrawReview(spuId)
                "off_shelf" -> repo.onshelf(spuId)
                else -> repo.offshelf(spuId)
            }
        }
    }

    fun adjustStock(skuId: Long, delta: Int) {
        _ui.value = _ui.value.copy(busy = true)
        viewModelScope.launch {
            repo.adjustInventory(skuId, delta, if (delta > 0) "商家补货" else "商家扣减").fold(
                onSuccess = { refreshSelection("库存已调整") },
                onFailure = { _ui.value = _ui.value.copy(busy = false, toast = errorMessage(it)) },
            )
        }
    }

    fun createSku(
        spuId: Long,
        skuCode: String,
        priceCents: Int,
        originalPriceCents: Int?,
        stock: Int,
        image: String,
    ) {
        _ui.value = _ui.value.copy(busy = true)
        viewModelScope.launch {
            repo.createSku(spuId, skuCode, emptyMap(), priceCents, originalPriceCents, stock, image).fold(
                onSuccess = { refreshSelection("SKU 已新增") },
                onFailure = { _ui.value = _ui.value.copy(busy = false, toast = errorMessage(it)) },
            )
        }
    }

    fun updateSku(
        spuId: Long,
        skuId: Long,
        priceCents: Int,
        originalPriceCents: Int?,
        image: String,
        isActive: Boolean,
    ) {
        _ui.value = _ui.value.copy(busy = true)
        viewModelScope.launch {
            repo.updateSku(spuId, skuId, priceCents, originalPriceCents, image, isActive).fold(
                onSuccess = { refreshSelection("SKU 已更新") },
                onFailure = { _ui.value = _ui.value.copy(busy = false, toast = errorMessage(it)) },
            )
        }
    }

    fun deleteSku(spuId: Long, skuId: Long) {
        _ui.value = _ui.value.copy(busy = true)
        viewModelScope.launch {
            repo.deleteSku(spuId, skuId).fold(
                onSuccess = { refreshSelection("SKU 已删除") },
                onFailure = { _ui.value = _ui.value.copy(busy = false, toast = errorMessage(it)) },
            )
        }
    }

    fun clearToast() {
        _ui.value = _ui.value.copy(toast = null)
    }

    private fun executeProductAction(successMessage: String, block: suspend () -> Result<SpuDetailDto>) {
        _ui.value = _ui.value.copy(busy = true)
        viewModelScope.launch {
            block().fold(
                onSuccess = {
                    _ui.value = _ui.value.copy(selectedSpu = it, busy = false, toast = successMessage)
                    load()
                    select(it.id)
                },
                onFailure = { _ui.value = _ui.value.copy(busy = false, toast = errorMessage(it)) },
            )
        }
    }

    private fun refreshSelection(message: String) {
        val selectedId = _ui.value.selectedSpu?.id
        _ui.value = _ui.value.copy(busy = false, toast = message)
        load()
        if (selectedId != null) {
            select(selectedId)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MerchantProductsScreen(vm: MerchantProductsViewModel = hiltViewModel()) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    var search by rememberSaveable { mutableStateOf("") }
    LaunchedEffect(Unit) { vm.load() }
    LaunchedEffect(ui.toast) {
        ui.toast?.let {
            snackbar.showSnackbar(it)
            vm.clearToast()
        }
    }
    Scaffold(
        topBar = { TopAppBar(title = { Text("商品管理") }) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { pad ->
        when (val state = ui.state) {
            UiState.Loading -> LoadingScreen(Modifier.padding(pad))
            is UiState.Error -> ErrorScreen(state.message, { vm.load(search) }, Modifier.padding(pad))
            is UiState.Success -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(pad),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item {
                        SearchAndCreateCard(
                            keyword = search,
                            onKeywordChange = { search = it },
                            onSearch = { vm.load(search) },
                            onCreate = vm::createSpu,
                            busy = ui.busy,
                        )
                    }
                    if (state.data.items.isEmpty()) {
                        item { EmptyState("未找到商品，试试新建一个") }
                    } else {
                        items(state.data.items) { spu ->
                            Card(modifier = Modifier.clickable { vm.select(spu.id) }) {
                                Column(
                                    Modifier.fillMaxWidth().padding(16.dp),
                                    verticalArrangement = Arrangement.spacedBy(6.dp),
                                ) {
                                    Text(spu.title, fontWeight = FontWeight.SemiBold)
                                    Text("销量：${spu.salesCount}")
                                    Text("最低价")
                                    PriceText(spu.minPriceCents)
                                }
                            }
                        }
                    }
                    ui.selectedSpu?.let { detail ->
                        item {
                            ProductDetailEditor(
                                detail = detail,
                                logs = ui.logs,
                                busy = ui.busy,
                                onUpdate = vm::updateSpu,
                                onDelete = vm::deleteSpu,
                                onToggleStatus = vm::changeStatus,
                                onAdjustStock = vm::adjustStock,
                                onCreateSku = vm::createSku,
                                onUpdateSku = vm::updateSku,
                                onDeleteSku = vm::deleteSku,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SearchAndCreateCard(
    keyword: String,
    onKeywordChange: (String) -> Unit,
    onSearch: () -> Unit,
    onCreate: (Long, Long?, String, String, String, String) -> Unit,
    busy: Boolean,
) {
    var categoryId by rememberSaveable { mutableStateOf("1") }
    var brandId by rememberSaveable { mutableStateOf("") }
    var title by rememberSaveable { mutableStateOf("") }
    var subtitle by rememberSaveable { mutableStateOf("") }
    var description by rememberSaveable { mutableStateOf("") }
    var mainImage by rememberSaveable { mutableStateOf("https://picsum.photos/seed/jdmerchant/600/600") }
    Card {
        Column(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("查找与新增商品", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = keyword,
                    onValueChange = onKeywordChange,
                    modifier = Modifier.weight(1f),
                    label = { Text("搜索商品") },
                )
                Button(onClick = onSearch, enabled = !busy) { Text("查找") }
            }
            OutlinedTextField(value = title, onValueChange = { title = it }, modifier = Modifier.fillMaxWidth(), label = { Text("商品标题") })
            OutlinedTextField(value = subtitle, onValueChange = { subtitle = it }, modifier = Modifier.fillMaxWidth(), label = { Text("商品副标题") })
            OutlinedTextField(value = description, onValueChange = { description = it }, modifier = Modifier.fillMaxWidth(), label = { Text("商品描述") })
            OutlinedTextField(value = categoryId, onValueChange = { categoryId = it }, modifier = Modifier.fillMaxWidth(), label = { Text("分类 ID") })
            OutlinedTextField(value = brandId, onValueChange = { brandId = it }, modifier = Modifier.fillMaxWidth(), label = { Text("品牌 ID（可空）") })
            OutlinedTextField(value = mainImage, onValueChange = { mainImage = it }, modifier = Modifier.fillMaxWidth(), label = { Text("主图地址") })
            Button(
                onClick = {
                    onCreate(
                        parseLongOrNull(categoryId) ?: 1L,
                        parseLongOrNull(brandId),
                        title.trim(),
                        subtitle.trim(),
                        description.trim(),
                        mainImage.trim(),
                    )
                },
                enabled = !busy && title.isNotBlank() && mainImage.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("新增草稿商品")
            }
        }
    }
}

@Composable
private fun ProductDetailEditor(
    detail: SpuDetailDto,
    logs: List<InventoryLogDto>,
    busy: Boolean,
    onUpdate: (Long, Long, Long?, String, String, String, String) -> Unit,
    onDelete: (Long) -> Unit,
    onToggleStatus: (Long, String) -> Unit,
    onAdjustStock: (Long, Int) -> Unit,
    onCreateSku: (Long, String, Int, Int?, Int, String) -> Unit,
    onUpdateSku: (Long, Long, Int, Int?, String, Boolean) -> Unit,
    onDeleteSku: (Long, Long) -> Unit,
) {
    var title by remember(detail.id) { mutableStateOf(detail.title) }
    var subtitle by remember(detail.id) { mutableStateOf(detail.subtitle.orEmpty()) }
    var description by remember(detail.id) { mutableStateOf(detail.description.orEmpty()) }
    var categoryId by remember(detail.id) { mutableStateOf(detail.categoryId.toString()) }
    var brandId by remember(detail.id) { mutableStateOf(detail.brandId?.toString().orEmpty()) }
    var mainImage by remember(detail.id) { mutableStateOf(detail.mainImage) }
    Card {
        Column(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("商品详情", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text("状态：${detail.status}")
            OutlinedTextField(value = title, onValueChange = { title = it }, modifier = Modifier.fillMaxWidth(), label = { Text("标题") })
            OutlinedTextField(value = subtitle, onValueChange = { subtitle = it }, modifier = Modifier.fillMaxWidth(), label = { Text("副标题") })
            OutlinedTextField(value = description, onValueChange = { description = it }, modifier = Modifier.fillMaxWidth(), label = { Text("描述") })
            OutlinedTextField(value = categoryId, onValueChange = { categoryId = it }, modifier = Modifier.fillMaxWidth(), label = { Text("分类 ID") })
            OutlinedTextField(value = brandId, onValueChange = { brandId = it }, modifier = Modifier.fillMaxWidth(), label = { Text("品牌 ID") })
            OutlinedTextField(value = mainImage, onValueChange = { mainImage = it }, modifier = Modifier.fillMaxWidth(), label = { Text("主图地址") })
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = {
                        onUpdate(
                            detail.id,
                            parseLongOrNull(categoryId) ?: detail.categoryId,
                            parseLongOrNull(brandId),
                            title,
                            subtitle,
                            description,
                            mainImage,
                        )
                    },
                    enabled = !busy,
                ) {
                    Text("保存商品")
                }
                OutlinedButton(onClick = { onToggleStatus(detail.id, detail.status) }, enabled = !busy) {
                    Text(
                        when (detail.status) {
                            "draft" -> "提交审核"
                            "pending_review" -> "撤回审核"
                            "off_shelf" -> "重新上架"
                            else -> "下架商品"
                        },
                    )
                }
                OutlinedButton(onClick = { onDelete(detail.id) }, enabled = !busy) {
                    Text("删除商品")
                }
            }
            Text("SKU 管理", fontWeight = FontWeight.SemiBold)
            detail.skus.forEach { sku ->
                SkuEditorCard(
                    spuId = detail.id,
                    sku = sku,
                    busy = busy,
                    onAdjustStock = onAdjustStock,
                    onUpdateSku = onUpdateSku,
                    onDeleteSku = onDeleteSku,
                )
            }
            CreateSkuCard(spuId = detail.id, busy = busy, onCreateSku = onCreateSku)
            if (logs.isNotEmpty()) {
                Text("最近库存日志", fontWeight = FontWeight.SemiBold)
                logs.take(5).forEach { log ->
                    Text("${log.createdAt.take(16)} 变动 ${log.delta}，结余 ${log.balanceAfter}")
                }
            }
        }
    }
}

@Composable
private fun SkuEditorCard(
    spuId: Long,
    sku: SkuDto,
    busy: Boolean,
    onAdjustStock: (Long, Int) -> Unit,
    onUpdateSku: (Long, Long, Int, Int?, String, Boolean) -> Unit,
    onDeleteSku: (Long, Long) -> Unit,
) {
    var price by remember(sku.id) { mutableStateOf(sku.priceCents.toString()) }
    var originalPrice by remember(sku.id) { mutableStateOf(sku.originalPriceCents?.toString().orEmpty()) }
    var image by remember(sku.id) { mutableStateOf(sku.image.orEmpty()) }
    var isActive by remember(sku.id) { mutableStateOf(sku.isActive) }
    Card {
        Column(
            Modifier.fillMaxWidth().padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("SKU ${sku.skuCode}", fontWeight = FontWeight.SemiBold)
            Text("库存 ${sku.stock}，销量 ${sku.soldCount}")
            OutlinedTextField(value = price, onValueChange = { price = it }, modifier = Modifier.fillMaxWidth(), label = { Text("售价（分）") })
            OutlinedTextField(value = originalPrice, onValueChange = { originalPrice = it }, modifier = Modifier.fillMaxWidth(), label = { Text("原价（分）") })
            OutlinedTextField(value = image, onValueChange = { image = it }, modifier = Modifier.fillMaxWidth(), label = { Text("图片地址") })
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(if (isActive) "已启用" else "已停用")
                Switch(checked = isActive, onCheckedChange = { isActive = it }, enabled = !busy)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = {
                        onUpdateSku(
                            spuId,
                            sku.id,
                            parseIntOrZero(price),
                            parseIntOrZero(originalPrice).takeIf { originalPrice.isNotBlank() },
                            image,
                            isActive,
                        )
                    },
                    enabled = !busy,
                ) {
                    Text("保存 SKU")
                }
                OutlinedButton(onClick = { onAdjustStock(sku.id, 5) }, enabled = !busy) { Text("库存 +5") }
                OutlinedButton(onClick = { onAdjustStock(sku.id, -2) }, enabled = !busy) { Text("库存 -2") }
                TextButton(onClick = { onDeleteSku(spuId, sku.id) }, enabled = !busy) { Text("删除") }
            }
        }
    }
}

@Composable
private fun CreateSkuCard(
    spuId: Long,
    busy: Boolean,
    onCreateSku: (Long, String, Int, Int?, Int, String) -> Unit,
) {
    var skuCode by remember(spuId) { mutableStateOf("") }
    var price by remember(spuId) { mutableStateOf("") }
    var originalPrice by remember(spuId) { mutableStateOf("") }
    var stock by remember(spuId) { mutableStateOf("0") }
    var image by remember(spuId) { mutableStateOf("") }
    Card {
        Column(
            Modifier.fillMaxWidth().padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("新增 SKU", fontWeight = FontWeight.SemiBold)
            OutlinedTextField(value = skuCode, onValueChange = { skuCode = it }, modifier = Modifier.fillMaxWidth(), label = { Text("SKU 编码") })
            OutlinedTextField(value = price, onValueChange = { price = it }, modifier = Modifier.fillMaxWidth(), label = { Text("售价（分）") })
            OutlinedTextField(value = originalPrice, onValueChange = { originalPrice = it }, modifier = Modifier.fillMaxWidth(), label = { Text("原价（分）") })
            OutlinedTextField(value = stock, onValueChange = { stock = it }, modifier = Modifier.fillMaxWidth(), label = { Text("初始库存") })
            OutlinedTextField(value = image, onValueChange = { image = it }, modifier = Modifier.fillMaxWidth(), label = { Text("图片地址") })
            Button(
                onClick = {
                    onCreateSku(
                        spuId,
                        skuCode.trim(),
                        parseIntOrZero(price),
                        parseIntOrZero(originalPrice).takeIf { originalPrice.isNotBlank() },
                        parseIntOrZero(stock),
                        image.trim(),
                    )
                },
                enabled = !busy && skuCode.isNotBlank() && price.isNotBlank(),
            ) {
                Text("新增 SKU")
            }
        }
    }
}

data class MerchantShippingUiState(val state: UiState<PageData<OrderListItemDto>> = UiState.Loading)

@HiltViewModel
class MerchantShippingViewModel @Inject constructor(private val repo: MerchantRepository) : ViewModel() {
    private val _ui = MutableStateFlow(MerchantShippingUiState())
    val ui: StateFlow<MerchantShippingUiState> = _ui.asStateFlow()

    fun load() {
        viewModelScope.launch {
            val result = repo.listOrders(status = "paid")
            _ui.value = MerchantShippingUiState(
                result.fold(
                    onSuccess = { UiState.Success(it) },
                    onFailure = { UiState.Error(errorMessage(it)) },
                ),
            )
        }
    }

    fun ship(orderId: Long) {
        viewModelScope.launch {
            repo.shipOrder(orderId, "JD-Express", "JD${System.currentTimeMillis().toString().takeLast(8)}")
            load()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MerchantShippingScreen(vm: MerchantShippingViewModel = hiltViewModel()) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { vm.load() }
    Scaffold(topBar = { TopAppBar(title = { Text("发货面板") }) }) { pad ->
        when (val state = ui.state) {
            UiState.Loading -> LoadingScreen(Modifier.padding(pad))
            is UiState.Error -> ErrorScreen(state.message, vm::load, Modifier.padding(pad))
            is UiState.Success -> {
                if (state.data.items.isEmpty()) {
                    EmptyState("当前没有待发货订单", modifier = Modifier.padding(pad))
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize().padding(pad),
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        items(state.data.items) { order ->
                            Card {
                                Column(
                                    Modifier.fillMaxWidth().padding(16.dp),
                                    verticalArrangement = Arrangement.spacedBy(8.dp),
                                ) {
                                    Text(order.orderNo, fontWeight = FontWeight.SemiBold)
                                    Text("收货人：${order.receiverName}")
                                    PriceText(order.totalCents)
                                    Button(onClick = { vm.ship(order.id) }) { Text("一键发货") }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

data class MerchantMessagesUiState(val state: UiState<List<NotificationDto>> = UiState.Loading)

@HiltViewModel
class MerchantMessagesViewModel @Inject constructor(private val repo: MerchantRepository) : ViewModel() {
    private val _ui = MutableStateFlow(MerchantMessagesUiState())
    val ui: StateFlow<MerchantMessagesUiState> = _ui.asStateFlow()

    fun load() {
        viewModelScope.launch {
            val result = repo.listNotifications()
            _ui.value = MerchantMessagesUiState(
                result.fold(
                    onSuccess = { UiState.Success(it.items) },
                    onFailure = { UiState.Error(errorMessage(it)) },
                ),
            )
        }
    }

    fun markAll() {
        viewModelScope.launch {
            repo.markAllNotificationsRead()
            load()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MerchantMessagesScreen(vm: MerchantMessagesViewModel = hiltViewModel()) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { vm.load() }
    Scaffold(topBar = { TopAppBar(title = { Text("消息中心") }) }) { pad ->
        when (val state = ui.state) {
            UiState.Loading -> LoadingScreen(Modifier.padding(pad))
            is UiState.Error -> ErrorScreen(state.message, vm::load, Modifier.padding(pad))
            is UiState.Success -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(pad),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item { OutlinedButton(onClick = vm::markAll) { Text("全部已读") } }
                    items(state.data) { message ->
                        Card {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(16.dp),
                                horizontalArrangement = Arrangement.spacedBy(12.dp),
                                verticalAlignment = Alignment.Top,
                            ) {
                                if (!message.isRead) {
                                    Box(
                                        modifier = Modifier
                                            .padding(top = 6.dp)
                                            .size(10.dp)
                                            .clip(MaterialTheme.shapes.small)
                                            .background(MaterialTheme.colorScheme.error),
                                    )
                                } else {
                                    SpacerDot()
                                }
                                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                    Text(message.title, fontWeight = FontWeight.SemiBold)
                                    Text(message.body)
                                    Text(
                                        if (message.isRead) "已读 ${message.createdAt.take(16)}" else "未读 ${message.createdAt.take(16)}",
                                        color = if (message.isRead) MaterialTheme.colorScheme.outline else MaterialTheme.colorScheme.error,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SpacerDot() {
    Box(modifier = Modifier.width(10.dp).height(10.dp))
}

data class MerchantReviewsUiState(
    val state: UiState<List<MerchantReviewDto>> = UiState.Loading,
    val submittingId: Long? = null,
    val toast: String? = null,
)

@HiltViewModel
class MerchantReviewsViewModel @Inject constructor(private val repo: MerchantRepository) : ViewModel() {
    private val _ui = MutableStateFlow(MerchantReviewsUiState())
    val ui: StateFlow<MerchantReviewsUiState> = _ui.asStateFlow()

    fun load() {
        viewModelScope.launch {
            val result = repo.listReviews()
            _ui.value = _ui.value.copy(
                state = result.fold(
                    onSuccess = { UiState.Success(it.items) },
                    onFailure = { UiState.Error(errorMessage(it)) },
                ),
                submittingId = null,
            )
        }
    }

    fun reply(review: MerchantReviewDto, content: String) {
        _ui.value = _ui.value.copy(submittingId = review.id)
        viewModelScope.launch {
            repo.replyReview(review.id, content, review.reply != null).fold(
                onSuccess = {
                    _ui.value = _ui.value.copy(submittingId = null, toast = "回复已提交")
                    load()
                },
                onFailure = {
                    _ui.value = _ui.value.copy(submittingId = null, toast = errorMessage(it))
                },
            )
        }
    }

    fun clearToast() {
        _ui.value = _ui.value.copy(toast = null)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MerchantReviewsScreen(vm: MerchantReviewsViewModel = hiltViewModel()) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(Unit) { vm.load() }
    LaunchedEffect(ui.toast) {
        ui.toast?.let {
            snackbar.showSnackbar(it)
            vm.clearToast()
        }
    }
    Scaffold(
        topBar = { TopAppBar(title = { Text("评价回复") }) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { pad ->
        when (val state = ui.state) {
            UiState.Loading -> LoadingScreen(Modifier.padding(pad))
            is UiState.Error -> ErrorScreen(state.message, vm::load, Modifier.padding(pad))
            is UiState.Success -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(pad),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(state.data) { review ->
                        var content by remember(review.id) {
                            mutableStateOf(review.reply?.content ?: "感谢您的支持，我们会继续优化商品与服务体验。")
                        }
                        val canSubmit = content.trim().length >= 5 && ui.submittingId != review.id
                        Card {
                            Column(
                                Modifier.fillMaxWidth().padding(16.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                Text(
                                    "评分 ${review.rating} · ${review.userDisplayName ?: "匿名用户"}",
                                    fontWeight = FontWeight.SemiBold,
                                )
                                Text(review.content)
                                OutlinedTextField(
                                    value = content,
                                    onValueChange = { content = it },
                                    modifier = Modifier.fillMaxWidth(),
                                    label = { Text("回复内容") },
                                    supportingText = { Text("至少 5 个字，提交后会自动刷新列表") },
                                )
                                Button(onClick = { vm.reply(review, content.trim()) }, enabled = canSubmit) {
                                    Text(
                                        when {
                                            ui.submittingId == review.id -> "提交中..."
                                            review.reply == null -> "发送回复"
                                            else -> "更新回复"
                                        },
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

data class MerchantDecorationUiState(
    val loading: Boolean = false,
    val merchant: MerchantMeDto? = null,
    val error: String? = null,
)

@HiltViewModel
class MerchantDecorationViewModel @Inject constructor(private val repo: MerchantRepository) : ViewModel() {
    private val _ui = MutableStateFlow(MerchantDecorationUiState())
    val ui: StateFlow<MerchantDecorationUiState> = _ui.asStateFlow()

    fun load() {
        viewModelScope.launch {
            repo.me().fold(
                onSuccess = { _ui.value = MerchantDecorationUiState(merchant = it) },
                onFailure = { _ui.value = MerchantDecorationUiState(error = errorMessage(it)) },
            )
        }
    }

    fun save(description: String, announcement: String, contactName: String, contactPhone: String) {
        _ui.value = _ui.value.copy(loading = true)
        viewModelScope.launch {
            repo.updateShop(description, announcement, contactName, contactPhone).fold(
                onSuccess = { _ui.value = MerchantDecorationUiState(merchant = it) },
                onFailure = { _ui.value = _ui.value.copy(loading = false, error = errorMessage(it)) },
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MerchantDecorationScreen(vm: MerchantDecorationViewModel = hiltViewModel()) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { vm.load() }
    Scaffold(topBar = { TopAppBar(title = { Text("店铺装修") }) }) { pad ->
        val merchant = ui.merchant
        if (merchant == null) {
            if (ui.error != null) ErrorScreen(ui.error!!, vm::load, Modifier.padding(pad)) else LoadingScreen(Modifier.padding(pad))
        } else {
            var description by remember(merchant.shop.id) { mutableStateOf(merchant.shop.description.orEmpty()) }
            var announcement by remember(merchant.shop.id) { mutableStateOf(merchant.shop.announcement.orEmpty()) }
            var contactName by remember(merchant.shop.id) { mutableStateOf(merchant.shop.contactName) }
            var contactPhone by remember(merchant.shop.id) { mutableStateOf(merchant.shop.contactPhone) }
            Column(
                modifier = Modifier.fillMaxSize().padding(pad).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                OutlinedTextField(value = description, onValueChange = { description = it }, modifier = Modifier.fillMaxWidth(), label = { Text("店铺简介") })
                OutlinedTextField(value = announcement, onValueChange = { announcement = it }, modifier = Modifier.fillMaxWidth(), label = { Text("店铺公告") })
                OutlinedTextField(value = contactName, onValueChange = { contactName = it }, modifier = Modifier.fillMaxWidth(), label = { Text("联系人") })
                OutlinedTextField(value = contactPhone, onValueChange = { contactPhone = it }, modifier = Modifier.fillMaxWidth(), label = { Text("联系电话") })
                Button(onClick = { vm.save(description, announcement, contactName, contactPhone) }, modifier = Modifier.fillMaxWidth()) {
                    Text(if (ui.loading) "保存中..." else "保存装修")
                }
            }
        }
    }
}

data class MerchantAccountUiState(val loading: Boolean = false)

@HiltViewModel
class MerchantAccountViewModel @Inject constructor(
    private val session: SessionState,
    private val authRepository: AuthRepository,
) : ViewModel() {
    val merchant = session.currentMerchant()
    private val _ui = MutableStateFlow(MerchantAccountUiState())
    val ui: StateFlow<MerchantAccountUiState> = _ui.asStateFlow()

    fun logout() {
        _ui.value = MerchantAccountUiState(loading = true)
        viewModelScope.launch {
            authRepository.logout()
            _ui.value = MerchantAccountUiState()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MerchantAccountScreen(
    onGoDecoration: () -> Unit,
    vm: MerchantAccountViewModel = hiltViewModel(),
) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val merchant = vm.merchant
    Scaffold(topBar = { TopAppBar(title = { Text("商家账号") }) }) { pad ->
        if (merchant == null) {
            EmptyState("未加载到商家信息", modifier = Modifier.padding(pad))
        } else {
            Column(
                modifier = Modifier.fillMaxSize().padding(pad).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Card {
                    Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(merchant.shop.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        Text("登录名：${merchant.account.loginName}")
                        Text("角色：${merchant.account.role}")
                        Text("联系人：${merchant.shop.contactName} ${merchant.shop.contactPhone}")
                    }
                }
                OutlinedButton(onClick = onGoDecoration, modifier = Modifier.fillMaxWidth()) { Text("进入店铺装修") }
                DangerButton(
                    text = "退出商家登录",
                    onClick = vm::logout,
                    loading = ui.loading,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}
