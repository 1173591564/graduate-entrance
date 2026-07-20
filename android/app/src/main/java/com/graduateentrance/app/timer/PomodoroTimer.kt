package com.graduateentrance.app.timer

import android.os.SystemClock
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

enum class PomodoroPhase { IDLE, RUNNING, PAUSED, FINISHED }

data class PomodoroState(
    val phase: PomodoroPhase = PomodoroPhase.IDLE,
    val taskId: String = "",
    val taskTitle: String = "",
    val totalSeconds: Int = 0,
    val remainingSeconds: Int = 0,
    val notice: String? = null,
) {
    val elapsedSeconds: Int get() = totalSeconds - remainingSeconds
    val elapsedMinutes: Int get() = if (elapsedSeconds <= 0) 0 else maxOf(1, elapsedSeconds / 60)
    val active: Boolean get() = phase == PomodoroPhase.RUNNING || phase == PomodoroPhase.PAUSED
}

/**
 * 基于时间戳的番茄钟：剩余时间按真实经过时长计算，
 * 即使进程被系统冻结/节流，恢复后 sync() 也能得到正确剩余时间。
 */
object PomodoroTimer {
    internal var clock: () -> Long = { SystemClock.elapsedRealtime() }

    private val _state = MutableStateFlow(PomodoroState())
    val state: StateFlow<PomodoroState> = _state.asStateFlow()

    private val _focusVisible = MutableStateFlow(false)
    val focusVisible: StateFlow<Boolean> = _focusVisible.asStateFlow()

    private var runningSince: Long? = null
    private var accumulatedMillis: Long = 0

    fun showFocus() {
        _focusVisible.value = true
    }

    fun hideFocus() {
        _focusVisible.value = false
    }

    fun start(taskId: String, taskTitle: String, minutes: Int, showFocus: Boolean = true): Boolean {
        if (_state.value.active || minutes <= 0) {
            return false
        }
        runningSince = clock()
        accumulatedMillis = 0
        _state.value = PomodoroState(
            phase = PomodoroPhase.RUNNING,
            taskId = taskId,
            taskTitle = taskTitle,
            totalSeconds = minutes * 60,
            remainingSeconds = minutes * 60,
        )
        _focusVisible.value = showFocus
        return true
    }

    fun pause() {
        _state.update { current ->
            if (current.phase != PomodoroPhase.RUNNING) return@update current
            accumulatedMillis += runningSince?.let { clock() - it } ?: 0
            runningSince = null
            current.copy(phase = PomodoroPhase.PAUSED, remainingSeconds = computeRemaining(current))
        }
    }

    fun resume() {
        _state.update { current ->
            if (current.phase != PomodoroPhase.PAUSED) return@update current
            runningSince = clock()
            current.copy(phase = PomodoroPhase.RUNNING)
        }
    }

    /** 按真实经过时间重算剩余时长；到点返回 true。 */
    fun sync(): Boolean {
        var finished = false
        _state.update { current ->
            if (current.phase != PomodoroPhase.RUNNING) {
                current
            } else {
                val remaining = computeRemaining(current)
                if (remaining <= 0) {
                    finished = true
                    runningSince = null
                    current.copy(phase = PomodoroPhase.FINISHED, remainingSeconds = 0)
                } else {
                    current.copy(remainingSeconds = remaining)
                }
            }
        }
        return finished
    }

    private fun computeRemaining(current: PomodoroState): Int {
        val elapsedMillis = accumulatedMillis + (runningSince?.let { clock() - it } ?: 0)
        return current.totalSeconds - (elapsedMillis / 1000).toInt()
    }

    fun cancel(): PomodoroState {
        sync()
        val snapshot = _state.value
        reset()
        return snapshot
    }

    fun finishWithNotice(notice: String) {
        _state.update { it.copy(phase = PomodoroPhase.FINISHED, notice = notice) }
        _focusVisible.value = false
    }

    fun clear() {
        reset()
    }

    private fun reset() {
        runningSince = null
        accumulatedMillis = 0
        _state.value = PomodoroState()
        _focusVisible.value = false
    }
}
