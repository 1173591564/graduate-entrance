package com.graduateentrance.app.timer

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.graduateentrance.app.R
import com.graduateentrance.app.data.CheckInResult
import com.graduateentrance.app.data.TodayRepository
import com.graduateentrance.app.data.local.AppDatabase
import com.graduateentrance.app.network.ApiClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class PomodoroService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var tickJob: Job? = null

    private val repository: TodayRepository by lazy {
        TodayRepository(ApiClient.service, AppDatabase.get(applicationContext).todayDao())
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                val taskId = intent.getStringExtra(EXTRA_TASK_ID).orEmpty()
                val taskTitle = intent.getStringExtra(EXTRA_TASK_TITLE).orEmpty()
                val minutes = intent.getIntExtra(EXTRA_MINUTES, DEFAULT_MINUTES)
                if (taskId.isNotEmpty() && PomodoroTimer.start(taskId, taskTitle, minutes)) {
                    startForegroundWithNotification()
                    startTicking()
                } else if (!PomodoroTimer.state.value.active) {
                    stopSelf()
                }
            }
            ACTION_PAUSE -> {
                PomodoroTimer.pause()
                updateNotification()
            }
            ACTION_RESUME -> {
                PomodoroTimer.resume()
                updateNotification()
            }
            ACTION_STOP -> {
                tickJob?.cancel()
                PomodoroTimer.cancel()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    private fun startTicking() {
        tickJob?.cancel()
        tickJob = scope.launch {
            while (true) {
                delay(1000)
                val finished = PomodoroTimer.tick()
                if (finished) {
                    completeSession()
                    break
                }
                if (!PomodoroTimer.state.value.active) {
                    break
                }
                updateNotification()
            }
        }
    }

    private suspend fun completeSession() {
        val state = PomodoroTimer.state.value
        val minutes = maxOf(1, state.totalSeconds / 60)
        val notice = when (repository.checkIn(state.taskId, minutes)) {
            CheckInResult.Synced -> "番茄钟完成，已自动打卡 $minutes 分钟"
            CheckInResult.Queued -> "番茄钟完成，打卡已入队，网络恢复后自动同步"
            is CheckInResult.Rejected -> "番茄钟完成，但打卡失败，请手动打卡"
        }
        PomodoroTimer.finishWithNotice(notice)
        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(FINISHED_NOTIFICATION_ID, buildFinishedNotification(state.taskTitle, notice))
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun startForegroundWithNotification() {
        createChannel()
        val notification = buildProgressNotification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE,
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun updateNotification() {
        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NOTIFICATION_ID, buildProgressNotification())
    }

    private fun buildProgressNotification(): Notification {
        val state = PomodoroTimer.state.value
        val minutes = state.remainingSeconds / 60
        val seconds = state.remainingSeconds % 60
        val paused = state.phase == PomodoroPhase.PAUSED
        val title = if (paused) "番茄钟已暂停" else "番茄钟进行中"
        val toggleAction = if (paused) {
            NotificationCompat.Action(0, "继续", actionIntent(ACTION_RESUME))
        } else {
            NotificationCompat.Action(0, "暂停", actionIntent(ACTION_PAUSE))
        }
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_pomodoro)
            .setContentTitle(title)
            .setContentText("%s · 剩余 %02d:%02d".format(state.taskTitle, minutes, seconds))
            .setOnlyAlertOnce(true)
            .setOngoing(true)
            .addAction(toggleAction)
            .addAction(NotificationCompat.Action(0, "放弃", actionIntent(ACTION_STOP)))
            .build()
    }

    private fun buildFinishedNotification(taskTitle: String, notice: String): Notification =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_pomodoro)
            .setContentTitle("番茄钟完成：$taskTitle")
            .setContentText(notice)
            .setAutoCancel(true)
            .build()

    private fun actionIntent(action: String): PendingIntent {
        val intent = Intent(this, PomodoroService::class.java).setAction(action)
        return PendingIntent.getService(
            this,
            action.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private fun createChannel() {
        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            CHANNEL_ID,
            "番茄钟",
            NotificationManager.IMPORTANCE_LOW,
        )
        manager.createNotificationChannel(channel)
    }

    companion object {
        const val DEFAULT_MINUTES = 25
        private const val CHANNEL_ID = "pomodoro"
        private const val NOTIFICATION_ID = 1001
        private const val FINISHED_NOTIFICATION_ID = 1002
        private const val ACTION_START = "com.graduateentrance.app.pomodoro.START"
        private const val ACTION_PAUSE = "com.graduateentrance.app.pomodoro.PAUSE"
        private const val ACTION_RESUME = "com.graduateentrance.app.pomodoro.RESUME"
        private const val ACTION_STOP = "com.graduateentrance.app.pomodoro.STOP"
        private const val EXTRA_TASK_ID = "task_id"
        private const val EXTRA_TASK_TITLE = "task_title"
        private const val EXTRA_MINUTES = "minutes"

        fun start(context: Context, taskId: String, taskTitle: String, minutes: Int) {
            val intent = Intent(context, PomodoroService::class.java)
                .setAction(ACTION_START)
                .putExtra(EXTRA_TASK_ID, taskId)
                .putExtra(EXTRA_TASK_TITLE, taskTitle)
                .putExtra(EXTRA_MINUTES, minutes)
            context.startForegroundService(intent)
        }

        fun pause(context: Context) = send(context, ACTION_PAUSE)

        fun resume(context: Context) = send(context, ACTION_RESUME)

        fun stop(context: Context) = send(context, ACTION_STOP)

        private fun send(context: Context, action: String) {
            context.startService(Intent(context, PomodoroService::class.java).setAction(action))
        }
    }
}
