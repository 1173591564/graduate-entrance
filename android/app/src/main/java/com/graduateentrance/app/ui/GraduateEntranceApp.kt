package com.graduateentrance.app.ui

import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.Network
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AutoStories
import androidx.compose.material.icons.outlined.ChatBubbleOutline
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.MenuBook
import androidx.compose.material.icons.outlined.PhotoCamera
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Sync
import androidx.compose.material.icons.outlined.Today
import androidx.compose.material.icons.outlined.Translate
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.rememberDrawerState
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.graduateentrance.app.data.CaptureRepository
import com.graduateentrance.app.data.ChatRepository
import com.graduateentrance.app.data.PapersRepository
import com.graduateentrance.app.data.RecitationRepository
import com.graduateentrance.app.data.ReviewsRepository
import com.graduateentrance.app.data.TodayRepository
import com.graduateentrance.app.data.VocabRepository
import com.graduateentrance.app.data.local.AppDatabase
import com.graduateentrance.app.network.ApiClient
import kotlinx.coroutines.launch
import androidx.compose.runtime.rememberCoroutineScope

@Composable
fun GraduateEntranceApp(
    initialCaptureUris: List<Uri> = emptyList(),
    onSharedUrisConsumed: () -> Unit = {},
) {
    val context = LocalContext.current.applicationContext
    val repository = remember {
        TodayRepository(ApiClient.service, AppDatabase.get(context).todayDao())
    }
    val todayViewModel: TodayViewModel = viewModel(factory = TodayViewModel.Factory(repository))
    val todayState by todayViewModel.uiState.collectAsState()
    val reviewsRepository = remember { ReviewsRepository(ApiClient.service) }
    val reviewsViewModel: ReviewsViewModel =
        viewModel(factory = ReviewsViewModel.Factory(reviewsRepository))
    val captureRepository = remember { CaptureRepository(ApiClient.service) }
    val captureViewModel: CaptureViewModel = viewModel(
        factory = CaptureViewModel.Factory(captureRepository) { uri ->
            loadCaptureImage(context, uri)
        },
    )
    val papersRepository = remember { PapersRepository(ApiClient.service) }
    val papersViewModel: PapersViewModel =
        viewModel(factory = PapersViewModel.Factory(papersRepository, context.cacheDir))
    val recitationRepository = remember { RecitationRepository(ApiClient.service) }
    val recitationViewModel: RecitationViewModel =
        viewModel(factory = RecitationViewModel.Factory(recitationRepository))
    val vocabRepository = remember { VocabRepository(ApiClient.service) }
    val vocabViewModel: VocabViewModel =
        viewModel(factory = VocabViewModel.Factory(vocabRepository))
    val chatRepository = remember { ChatRepository(ApiClient.service) }
    val chatViewModel: ChatViewModel = viewModel(
        factory = ChatViewModel.Factory(chatRepository) { uri ->
            loadCaptureImage(context, uri)
        },
    )
    var destination by rememberSaveable { mutableStateOf(AppDestination.HOME) }
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()

    LaunchedEffect(initialCaptureUris) {
        if (initialCaptureUris.isNotEmpty()) {
            captureViewModel.addImages(initialCaptureUris)
            destination = AppDestination.CAPTURE
            onSharedUrisConsumed()
        }
    }

    DisposableEffect(context) {
        val connectivityManager =
            context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                todayViewModel.onNetworkAvailable()
            }
        }
        connectivityManager.registerDefaultNetworkCallback(callback)
        onDispose {
            connectivityManager.unregisterNetworkCallback(callback)
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            AppDrawer(
                todayState = todayState,
                destination = destination,
                onNavigate = {
                    destination = it
                    scope.launch { drawerState.close() }
                },
            )
        },
    ) {
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            containerColor = MaterialTheme.colorScheme.background,
            bottomBar = {
                if (destination != AppDestination.SETTINGS) {
                    AppBottomBar(
                        destination = destination,
                        onNavigate = {
                            destination = it
                            if (it == AppDestination.REVIEWS) {
                                reviewsViewModel.refresh()
                            }
                            if (it == AppDestination.PAPERS) {
                                papersViewModel.refresh()
                            }
                            if (it == AppDestination.RECITATION) {
                                recitationViewModel.refresh()
                            }
                            if (it == AppDestination.VOCAB) {
                                vocabViewModel.refresh()
                            }
                            if (it == AppDestination.CHAT) {
                                chatViewModel.refreshConversations()
                            }
                        },
                    )
                }
            },
        ) { innerPadding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
            ) {
                when (destination) {
                    AppDestination.HOME -> HomeScreen(
                        state = todayState,
                        onOpenDrawer = { scope.launch { drawerState.open() } },
                        onNavigate = { destination = it },
                        onAskChat = { draft ->
                            chatViewModel.prefillInput(draft)
                            chatViewModel.refreshConversations()
                            destination = AppDestination.CHAT
                        },
                    )
                    AppDestination.CHAT -> ChatScreen(viewModel = chatViewModel)
                    AppDestination.TODAY -> TodayScreen(viewModel = todayViewModel)
                    AppDestination.REVIEWS -> ReviewsScreen(viewModel = reviewsViewModel)
                    AppDestination.PAPERS -> PapersScreen(viewModel = papersViewModel)
                    AppDestination.RECITATION -> RecitationScreen(viewModel = recitationViewModel)
                    AppDestination.VOCAB -> VocabScreen(viewModel = vocabViewModel)
                    AppDestination.CAPTURE -> CaptureScreen(viewModel = captureViewModel)
                    AppDestination.SETTINGS -> SettingsScreen(
                        todayState = todayState,
                        onBack = { destination = AppDestination.HOME },
                    )
                }
            }
        }
    }
}


@Composable
private fun AppBottomBar(
    destination: AppDestination,
    onNavigate: (AppDestination) -> Unit,
) {
    NavigationBar(
        containerColor = MaterialTheme.colorScheme.surface,
        tonalElevation = 0.dp,
    ) {
        bottomItems.forEach { item ->
            NavigationBarItem(
                selected = destination == item.destination,
                onClick = { onNavigate(item.destination) },
                icon = {
                    Icon(
                        imageVector = item.icon,
                        contentDescription = item.label,
                    )
                },
                label = { Text(item.label) },
            )
        }
    }
}

private data class NavItem(
    val destination: AppDestination,
    val label: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
)

private val bottomItems = listOf(
    NavItem(AppDestination.HOME, "首页", Icons.Outlined.Home),
    NavItem(AppDestination.CHAT, "问答", Icons.Outlined.ChatBubbleOutline),
    NavItem(AppDestination.TODAY, "今日", Icons.Outlined.Today),
    NavItem(AppDestination.VOCAB, "背单词", Icons.Outlined.Translate),
    NavItem(AppDestination.RECITATION, "一背", Icons.Outlined.AutoStories),
    NavItem(AppDestination.CAPTURE, "拍题", Icons.Outlined.PhotoCamera),
)

private val drawerItems = listOf(
    NavItem(AppDestination.HOME, "首页", Icons.Outlined.Home),
    NavItem(AppDestination.CHAT, "ChatLearning 问答", Icons.Outlined.ChatBubbleOutline),
    NavItem(AppDestination.TODAY, "今日", Icons.Outlined.Today),
    NavItem(AppDestination.VOCAB, "背单词", Icons.Outlined.Translate),
    NavItem(AppDestination.RECITATION, "一背", Icons.Outlined.AutoStories),
    NavItem(AppDestination.PAPERS, "阅读", Icons.Outlined.MenuBook),
    NavItem(AppDestination.REVIEWS, "错题复习", Icons.Outlined.AutoStories),
    NavItem(AppDestination.CAPTURE, "拍题", Icons.Outlined.PhotoCamera),
    NavItem(AppDestination.SETTINGS, "设置", Icons.Outlined.Settings),
)

@Composable
private fun AppDrawer(
    todayState: TodayUiState,
    destination: AppDestination,
    onNavigate: (AppDestination) -> Unit,
) {
    ModalDrawerSheet {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text("11408 备考", style = MaterialTheme.typography.titleLarge)
            SyncStatusCard(todayState)
            drawerItems.forEach { item ->
                NavigationDrawerItem(
                    selected = destination == item.destination,
                    onClick = { onNavigate(item.destination) },
                    icon = { Icon(item.icon, contentDescription = null) },
                    label = { Text(item.label) },
                )
            }
        }
    }
}

@Composable
private fun SyncStatusCard(todayState: TodayUiState) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.Sync, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("连接状态", style = MaterialTheme.typography.titleMedium)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                AppStatusChip(
                    label = if (todayState.fromCache) "离线缓存" else "在线",
                    tone = if (todayState.fromCache) NoticeTone.OFFLINE else NoticeTone.SUCCESS,
                )
                AppStatusChip(
                    label = if (todayState.pendingCheckIns > 0) {
                        "${todayState.pendingCheckIns} 待同步"
                    } else {
                        "已同步"
                    },
                    tone = if (todayState.pendingCheckIns > 0) {
                        NoticeTone.WARNING
                    } else {
                        NoticeTone.SUCCESS
                    },
                )
            }
            Spacer(Modifier.height(2.dp))
            Text(
                text = "今日 ${todayState.completedMinutes}/${todayState.plannedMinutes} 分钟",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
