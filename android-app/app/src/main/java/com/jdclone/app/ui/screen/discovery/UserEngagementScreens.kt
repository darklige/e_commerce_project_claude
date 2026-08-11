package com.jdclone.app.ui.screen.discovery

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.jdclone.app.data.network.dto.CampaignDto
import com.jdclone.app.data.network.dto.CouponDto
import com.jdclone.app.data.network.dto.FavoriteSpuDto
import com.jdclone.app.data.network.dto.FollowedShopDto
import com.jdclone.app.data.network.dto.FootprintDto
import com.jdclone.app.data.repository.DiscoveryRepository
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

@HiltViewModel
class ActivityHallViewModel @Inject constructor(
    private val repo: DiscoveryRepository,
) : ViewModel() {
    private val _ui = MutableStateFlow<UiState<CampaignDto>>(UiState.Loading)
    val ui: StateFlow<UiState<CampaignDto>> = _ui.asStateFlow()

    fun load() {
        _ui.value = UiState.Loading
        viewModelScope.launch {
            _ui.value = repo.getActiveCampaign().fold(
                onSuccess = { UiState.Success(it) },
                onFailure = { UiState.Error(errorMessage(it)) },
            )
        }
    }
}

@HiltViewModel
class CouponCenterViewModel @Inject constructor(
    private val repo: DiscoveryRepository,
) : ViewModel() {
    private val _ui = MutableStateFlow<UiState<List<CouponDto>>>(UiState.Loading)
    val ui: StateFlow<UiState<List<CouponDto>>> = _ui.asStateFlow()

    fun load() {
        _ui.value = UiState.Loading
        viewModelScope.launch {
            _ui.value = repo.listCoupons().fold(
                onSuccess = { UiState.Success(it) },
                onFailure = { UiState.Error(errorMessage(it)) },
            )
        }
    }

    fun claim(id: String) {
        viewModelScope.launch {
            repo.claimCoupon(id)
            load()
        }
    }
}

@HiltViewModel
class FavoritesViewModel @Inject constructor(
    private val repo: DiscoveryRepository,
) : ViewModel() {
    private val _ui = MutableStateFlow<UiState<List<FavoriteSpuDto>>>(UiState.Loading)
    val ui: StateFlow<UiState<List<FavoriteSpuDto>>> = _ui.asStateFlow()

    fun load() {
        _ui.value = UiState.Loading
        viewModelScope.launch {
            _ui.value = repo.listFavorites().fold(
                onSuccess = { UiState.Success(it) },
                onFailure = { UiState.Error(errorMessage(it)) },
            )
        }
    }

    fun toggle(spuId: Long) {
        viewModelScope.launch {
            repo.toggleFavorite(spuId)
            load()
        }
    }
}

@HiltViewModel
class FollowsViewModel @Inject constructor(
    private val repo: DiscoveryRepository,
) : ViewModel() {
    private val _ui = MutableStateFlow<UiState<List<FollowedShopDto>>>(UiState.Loading)
    val ui: StateFlow<UiState<List<FollowedShopDto>>> = _ui.asStateFlow()

    fun load() {
        _ui.value = UiState.Loading
        viewModelScope.launch {
            _ui.value = repo.listFollows().fold(
                onSuccess = { UiState.Success(it) },
                onFailure = { UiState.Error(errorMessage(it)) },
            )
        }
    }

    fun toggle(shopId: Long) {
        viewModelScope.launch {
            repo.toggleFollow(shopId)
            load()
        }
    }
}

@HiltViewModel
class FootprintsViewModel @Inject constructor(
    private val repo: DiscoveryRepository,
) : ViewModel() {
    private val _ui = MutableStateFlow<UiState<List<FootprintDto>>>(UiState.Loading)
    val ui: StateFlow<UiState<List<FootprintDto>>> = _ui.asStateFlow()

    fun load() {
        _ui.value = UiState.Loading
        viewModelScope.launch {
            _ui.value = repo.listFootprints().fold(
                onSuccess = { UiState.Success(it) },
                onFailure = { UiState.Error(errorMessage(it)) },
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ActivityHallScreen(
    onBack: () -> Unit,
    onOpenCoupons: () -> Unit,
    onOpenProduct: (Long) -> Unit,
    vm: ActivityHallViewModel = hiltViewModel(),
) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { vm.load() }
    Scaffold(topBar = { TopAppBar(title = { Text("活动会场") }) }) { pad ->
        when (val state = ui) {
            UiState.Loading -> LoadingScreen(Modifier.padding(pad))
            is UiState.Error -> ErrorScreen(state.message, vm::load, Modifier.padding(pad))
            is UiState.Success -> {
                val campaign = state.data
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(pad),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item {
                        Card {
                            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text(campaign.title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                                Text(campaign.subtitle)
                                Text(campaign.bannerText, color = MaterialTheme.colorScheme.primary)
                                campaign.fullReductionRules.forEach { Text("• $it") }
                                Button(onClick = onOpenCoupons) { Text("查看可领优惠券") }
                            }
                        }
                    }
                    campaign.featuredSections.forEach { section ->
                        item { Text(section.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold) }
                        items(section.items) { spu ->
                            Card(modifier = Modifier.clickable { onOpenProduct(spu.id) }) {
                                Row(
                                    Modifier.fillMaxWidth().padding(16.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                ) {
                                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                        Text(spu.title, fontWeight = FontWeight.SemiBold)
                                        Text(section.subtitle, color = MaterialTheme.colorScheme.outline)
                                    }
                                    PriceText(spu.minPriceCents)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CouponCenterScreen(
    onBack: () -> Unit,
    vm: CouponCenterViewModel = hiltViewModel(),
) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { vm.load() }
    Scaffold(topBar = { TopAppBar(title = { Text("优惠券中心") }) }) { pad ->
        when (val state = ui) {
            UiState.Loading -> LoadingScreen(Modifier.padding(pad))
            is UiState.Error -> ErrorScreen(state.message, vm::load, Modifier.padding(pad))
            is UiState.Success -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(pad),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(state.data) { coupon ->
                        Card {
                            Row(
                                Modifier.fillMaxWidth().padding(16.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Text(coupon.title, fontWeight = FontWeight.SemiBold)
                                    Text(coupon.discountLabel, color = MaterialTheme.colorScheme.primary)
                                    Text(coupon.thresholdLabel)
                                    Text(coupon.scopeLabel, color = MaterialTheme.colorScheme.outline)
                                }
                                if (coupon.claimed) {
                                    Text("已领取", color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(top = 6.dp))
                                } else {
                                    OutlinedButton(onClick = { vm.claim(coupon.id) }) { Text("领取") }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FavoritesScreen(
    onBack: () -> Unit,
    onOpenProduct: (Long) -> Unit,
    vm: FavoritesViewModel = hiltViewModel(),
) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { vm.load() }
    ItemListScaffold("我的收藏", onBack, ui, vm::load) { items ->
        if (items.isEmpty()) {
            EmptyState("还没有收藏商品")
        } else {
            LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                items(items) { favorite ->
                    Card {
                        Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Column(Modifier.weight(1f).clickable { onOpenProduct(favorite.spu.id) }, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(favorite.spu.title, fontWeight = FontWeight.SemiBold)
                                Text("收藏时间 ${favorite.collectedAt.take(16)}", color = MaterialTheme.colorScheme.outline)
                            }
                            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                PriceText(favorite.spu.minPriceCents)
                                OutlinedButton(onClick = { vm.toggle(favorite.spu.id) }) { Text("取消") }
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FollowsScreen(
    onBack: () -> Unit,
    vm: FollowsViewModel = hiltViewModel(),
) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { vm.load() }
    ItemListScaffold("店铺关注", onBack, ui, vm::load) { items ->
        if (items.isEmpty()) {
            EmptyState("还没有关注店铺")
        } else {
            LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                items(items) { shop ->
                    Card {
                        Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(shop.name, fontWeight = FontWeight.SemiBold)
                                if (!shop.announcement.isNullOrBlank()) Text(shop.announcement!!)
                                Text("销量 ${shop.salesCount} · 评分 ${shop.ratingAvg}", color = MaterialTheme.colorScheme.outline)
                            }
                            OutlinedButton(onClick = { vm.toggle(shop.id) }) { Text("取消关注") }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FootprintsScreen(
    onBack: () -> Unit,
    onOpenProduct: (Long) -> Unit,
    vm: FootprintsViewModel = hiltViewModel(),
) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { vm.load() }
    ItemListScaffold("浏览足迹", onBack, ui, vm::load) { items ->
        if (items.isEmpty()) {
            EmptyState("最近还没有浏览记录")
        } else {
            LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                items(items) { footprint ->
                    Card(modifier = Modifier.clickable { onOpenProduct(footprint.spu.id) }) {
                        Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(footprint.spu.title, fontWeight = FontWeight.SemiBold)
                                Text("浏览时间 ${footprint.viewedAt.take(16)}", color = MaterialTheme.colorScheme.outline)
                            }
                            PriceText(footprint.spu.minPriceCents)
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun <T> ItemListScaffold(
    title: String,
    onBack: () -> Unit,
    ui: UiState<List<T>>,
    onRetry: () -> Unit,
    content: @Composable (List<T>) -> Unit,
) {
    Scaffold(topBar = { TopAppBar(title = { Text(title) }) }) { pad ->
        when (ui) {
            UiState.Loading -> LoadingScreen(Modifier.padding(pad))
            is UiState.Error -> ErrorScreen(ui.message, onRetry, Modifier.padding(pad))
            is UiState.Success -> content(ui.data)
        }
    }
}
