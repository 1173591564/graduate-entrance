package com.graduateentrance.app.ui

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AutoStories
import androidx.compose.material.icons.outlined.PhotoCamera
import androidx.compose.material.icons.outlined.Today
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.graduateentrance.app.data.CaptureRepository
import com.graduateentrance.app.data.ReviewsRepository
import com.graduateentrance.app.data.TodayRepository
import com.graduateentrance.app.data.local.AppDatabase
import com.graduateentrance.app.network.ApiClient

@Composable
fun GraduateEntranceApp() {
    val context = LocalContext.current.applicationContext
    val repository = remember {
        TodayRepository(ApiClient.service, AppDatabase.get(context).todayDao())
    }
    val todayViewModel: TodayViewModel = viewModel(factory = TodayViewModel.Factory(repository))
    val reviewsRepository = remember { ReviewsRepository(ApiClient.service) }
    val reviewsViewModel: ReviewsViewModel =
        viewModel(factory = ReviewsViewModel.Factory(reviewsRepository))
    val captureRepository = remember { CaptureRepository(ApiClient.service) }
    val captureViewModel: CaptureViewModel = viewModel(
        factory = CaptureViewModel.Factory(captureRepository) { uri ->
            loadCaptureImage(context, uri)
        },
    )
    var selectedTab by rememberSaveable { mutableIntStateOf(0) }

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

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = androidx.compose.material3.MaterialTheme.colorScheme.background,
        bottomBar = {
            NavigationBar(
                containerColor = androidx.compose.material3.MaterialTheme.colorScheme.surface,
                tonalElevation = 0.dp,
            ) {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = {
                        Icon(
                            imageVector = Icons.Outlined.Today,
                            contentDescription = "今日",
                        )
                    },
                    label = { Text("今日") },
                )
                NavigationBarItem(
                    selected = selectedTab == 1,
                    onClick = {
                        selectedTab = 1
                        reviewsViewModel.refresh()
                    },
                    icon = {
                        Icon(
                            imageVector = Icons.Outlined.AutoStories,
                            contentDescription = "复习",
                        )
                    },
                    label = { Text("复习") },
                )
                NavigationBarItem(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    icon = {
                        Icon(
                            imageVector = Icons.Outlined.PhotoCamera,
                            contentDescription = "拍题",
                        )
                    },
                    label = { Text("拍题") },
                )
            }
        },
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
        ) {
            when (selectedTab) {
                0 -> TodayScreen(viewModel = todayViewModel)
                1 -> ReviewsScreen(viewModel = reviewsViewModel)
                else -> CaptureScreen(viewModel = captureViewModel)
            }
        }
    }
}
