package com.jdclone.app.ui.screen.catalog

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.jdclone.app.data.network.dto.CategoryDto
import com.jdclone.app.ui.common.ErrorScreen
import com.jdclone.app.ui.common.LoadingScreen
import com.jdclone.app.ui.common.RemoteImage
import com.jdclone.app.ui.common.UiState

/** 分类 tab 主页 —— 左侧一级 + 右侧二/三级。 */
@Composable
fun CategoryScreen(
    onGoCategory: (Long) -> Unit,
    vm: HomeViewModel = hiltViewModel(),
) {
    val state by vm.state.collectAsStateWithLifecycle()

    when (val s = state) {
        UiState.Loading -> LoadingScreen()
        is UiState.Error -> ErrorScreen(s.message, onRetry = vm::load)
        is UiState.Success -> CategoryContent(s.data.categories, onGoCategory)
    }
}

@Composable
private fun CategoryContent(
    roots: List<CategoryDto>,
    onGoCategory: (Long) -> Unit,
) {
    if (roots.isEmpty()) {
        Text(
            text = "暂无分类",
            modifier = Modifier.padding(24.dp),
        )
        return
    }
    var selected by rememberSaveable { mutableIntStateOf(0) }
    Row(modifier = Modifier.fillMaxSize()) {
        // 左侧一级
        LazyColumn(
            modifier = Modifier
                .width(96.dp)
                .fillMaxHeight()
                .background(MaterialTheme.colorScheme.surfaceVariant),
        ) {
            items(roots, key = { it.id }) { root ->
                val active = roots.getOrNull(selected)?.id == root.id
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable {
                            selected = roots.indexOf(root)
                        }
                        .padding(vertical = 14.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = root.name,
                        color = if (active) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                        style = if (active) MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold)
                        else MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }
        // 右侧二/三级
        val current = roots.getOrNull(selected)
        if (current != null) {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                items(current.children, key = { it.id }) { sub ->
                    Column {
                        Text(
                            text = sub.name,
                            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
                            modifier = Modifier.padding(bottom = 6.dp),
                        )
                        val leaves = sub.children.ifEmpty { listOf(sub) }.chunked(3)
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            leaves.forEach { rowItems ->
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                ) {
                                    rowItems.forEach { leaf ->
                                        CategoryLeafCard(
                                            leaf = leaf,
                                            modifier = Modifier.weight(1f),
                                            onClick = { onGoCategory(leaf.id) },
                                        )
                                    }
                                    repeat(3 - rowItems.size) {
                                        Spacer(modifier = Modifier.weight(1f))
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

@Composable
private fun CategoryLeafCard(
    leaf: CategoryDto,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    Card(
        onClick = onClick,
        modifier = modifier,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(RoundedCornerShape(24.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
            ) {
                RemoteImage(
                    objectKey = leaf.iconUrl,
                    modifier = Modifier.fillMaxSize(),
                    cornerRadiusDp = 24,
                )
            }
            Spacer(Modifier.size(4.dp))
            Text(
                leaf.name,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
            )
        }
    }
}
