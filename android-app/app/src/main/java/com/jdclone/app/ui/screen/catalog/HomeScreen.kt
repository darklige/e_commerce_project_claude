package com.jdclone.app.ui.screen.catalog

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.jdclone.app.data.network.dto.CategoryDto
import com.jdclone.app.data.network.dto.SpuListItemDto
import com.jdclone.app.ui.common.ErrorScreen
import com.jdclone.app.ui.common.LoadingScreen
import com.jdclone.app.ui.common.PriceText
import com.jdclone.app.ui.common.RemoteImage
import com.jdclone.app.ui.common.UiState

@Composable
fun HomeScreen(
    onGoSearch: () -> Unit,
    onGoProduct: (Long) -> Unit,
    onGoCategory: (Long) -> Unit,
    onGoActivityHall: () -> Unit,
    onGoCouponCenter: () -> Unit,
    vm: HomeViewModel = hiltViewModel(),
) {
    val state by vm.state.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        Surface(
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Surface(
                    color = MaterialTheme.colorScheme.surface,
                    shape = RoundedCornerShape(24.dp),
                    modifier = Modifier.weight(1f).height(40.dp).clickable { onGoSearch() },
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(Icons.Outlined.Search, contentDescription = null, tint = MaterialTheme.colorScheme.outline)
                        Spacer(Modifier.width(8.dp))
                        Text("搜索商品", color = MaterialTheme.colorScheme.outline, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }

        when (val s = state) {
            UiState.Loading -> LoadingScreen()
            is UiState.Error -> ErrorScreen(s.message, onRetry = vm::load)
            is UiState.Success -> HomeContent(s.data, onGoProduct, onGoCategory, onGoActivityHall, onGoCouponCenter)
        }
    }
}

@Composable
private fun HomeContent(
    data: HomeState,
    onGoProduct: (Long) -> Unit,
    onGoCategory: (Long) -> Unit,
    onGoActivityHall: () -> Unit,
    onGoCouponCenter: () -> Unit,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Card(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp).clickable { onGoActivityHall() },
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("818 数码家电会场", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        Text("模拟活动已开启，可领券、看满减、逛会场")
                    }
                    Text(
                        "领券",
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.clickable { onGoCouponCenter() },
                    )
                }
            }
        }
        item { SectionHeader("常用类目") }
        item {
            LazyVerticalGrid(
                columns = GridCells.Fixed(4),
                modifier = Modifier.fillMaxWidth().height((data.categories.size.coerceAtLeast(1) / 4 + 1).let { rows -> (rows * 92).dp.coerceAtMost(300.dp) }),
                contentPadding = PaddingValues(horizontal = 12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                userScrollEnabled = false,
            ) {
                items(data.categories.take(8), key = { it.id }) { cat ->
                    CategoryGridItem(cat, onClick = { onGoCategory(cat.id) })
                }
            }
        }
        item { SectionHeader("为你推荐") }
        item {
            LazyRow(
                modifier = Modifier.fillMaxWidth(),
                contentPadding = PaddingValues(horizontal = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(data.recommendations, key = { it.id }) { spu ->
                    RecommendationCard(spu, onClick = { onGoProduct(spu.id) })
                }
            }
        }
        item { Spacer(Modifier.height(32.dp)) }
    }
}

@Composable
private fun SectionHeader(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
        modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
    )
}

@Composable
private fun CategoryGridItem(cat: CategoryDto, onClick: () -> Unit) {
    Column(
        modifier = Modifier.clickable { onClick() }.padding(6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier.size(56.dp).clip(RoundedCornerShape(28.dp)).background(MaterialTheme.colorScheme.surfaceVariant),
        ) {
            RemoteImage(objectKey = cat.iconUrl, modifier = Modifier.fillMaxSize(), cornerRadiusDp = 28)
        }
        Spacer(Modifier.height(4.dp))
        Text(cat.name, style = MaterialTheme.typography.bodySmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun RecommendationCard(spu: SpuListItemDto, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.width(140.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column {
            RemoteImage(objectKey = spu.mainImage, modifier = Modifier.fillMaxWidth().aspectRatio(1f), cornerRadiusDp = 4)
            Column(modifier = Modifier.padding(8.dp)) {
                Text(spu.title, style = MaterialTheme.typography.bodySmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Spacer(Modifier.height(4.dp))
                PriceText(spu.minPriceCents, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
