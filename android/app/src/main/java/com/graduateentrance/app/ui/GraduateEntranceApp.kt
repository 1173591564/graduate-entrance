package com.graduateentrance.app.ui

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
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
import androidx.lifecycle.viewmodel.compose.viewModel
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

    Column(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.weight(1f)) {
            when (selectedTab) {
                0 -> TodayScreen(viewModel = todayViewModel)
                else -> ReviewsScreen(viewModel = reviewsViewModel)
            }
        }
        NavigationBar {
            NavigationBarItem(
                selected = selectedTab == 0,
                onClick = { selectedTab = 0 },
                icon = { Text("日") },
                label = { Text("今日") },
            )
            NavigationBarItem(
                selected = selectedTab == 1,
                onClick = {
                    selectedTab = 1
                    reviewsViewModel.refresh()
                },
                icon = { Text("复") },
                label = { Text("复习") },
            )
        }
    }
}
