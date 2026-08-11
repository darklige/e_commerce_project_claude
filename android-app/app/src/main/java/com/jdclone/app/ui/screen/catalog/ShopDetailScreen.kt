package com.jdclone.app.ui.screen.catalog

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.jdclone.app.data.network.PageData
import com.jdclone.app.data.network.dto.ShopPublicDto
import com.jdclone.app.data.network.dto.SpuListItemDto
import com.jdclone.app.data.repository.CatalogRepository
import com.jdclone.app.ui.common.ErrorScreen
import com.jdclone.app.ui.common.LoadingScreen
import com.jdclone.app.ui.common.PriceText
import com.jdclone.app.ui.common.RemoteImage
import com.jdclone.app.ui.common.UiState
import com.jdclone.app.ui.common.errorMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

data class ShopDetailUiState(
    val state: UiState<Pair<ShopPublicDto, PageData<SpuListItemDto>>> = UiState.Loading,
)

@HiltViewModel
class ShopDetailViewModel @Inject constructor(
    private val repo: CatalogRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {
    private val shopId: Long = savedStateHandle.get<String>("id")?.toLongOrNull() ?: 0L
    private val _ui = MutableStateFlow(ShopDetailUiState())
    val ui: StateFlow<ShopDetailUiState> = _ui.asStateFlow()

    fun load() {
        _ui.value = ShopDetailUiState(UiState.Loading)
        viewModelScope.launch {
            val shop = repo.getShop(shopId)
            val spus = repo.listShopSpus(shopId)
            _ui.value = if (shop.isSuccess && spus.isSuccess) {
                ShopDetailUiState(UiState.Success(shop.getOrThrow() to spus.getOrThrow()))
            } else {
                ShopDetailUiState(UiState.Error(errorMessage(shop.exceptionOrNull() ?: spus.exceptionOrNull()!!)))
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShopDetailScreen(
    onBack: () -> Unit,
    onGoProduct: (Long) -> Unit,
    vm: ShopDetailViewModel = hiltViewModel(),
) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { vm.load() }
    Scaffold(topBar = { TopAppBar(title = { Text("店铺详情") }) }) { pad ->
        when (val state = ui.state) {
            UiState.Loading -> LoadingScreen(Modifier.padding(pad))
            is UiState.Error -> ErrorScreen(state.message, vm::load, Modifier.padding(pad))
            is UiState.Success -> {
                val (shop, page) = state.data
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(pad),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item {
                        Card {
                            Column(
                                modifier = Modifier.fillMaxWidth().padding(16.dp),
                                verticalArrangement = Arrangement.spacedBy(6.dp),
                            ) {
                                Text(shop.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                                if (!shop.announcement.isNullOrBlank()) {
                                    Text(shop.announcement!!)
                                }
                                if (!shop.description.isNullOrBlank()) {
                                    Text(shop.description!!)
                                }
                                Text("销量 ${shop.salesCount} · 评分 ${shop.ratingAvg}")
                            }
                        }
                    }
                    items(page.items) { spu ->
                        Card(onClick = { onGoProduct(spu.id) }) {
                            Column(
                                modifier = Modifier.fillMaxWidth().padding(12.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                RemoteImage(objectKey = spu.mainImage, modifier = Modifier.fillMaxWidth(), cornerRadiusDp = 8)
                                Text(spu.title, fontWeight = FontWeight.SemiBold)
                                PriceText(spu.minPriceCents)
                            }
                        }
                    }
                }
            }
        }
    }
}
