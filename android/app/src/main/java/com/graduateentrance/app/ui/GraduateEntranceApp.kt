package com.graduateentrance.app.ui

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
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

    TodayScreen(viewModel = todayViewModel)
}
