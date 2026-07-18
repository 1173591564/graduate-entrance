package com.graduateentrance.app.timer

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

object PomodoroTimer {
    private val _state = MutableStateFlow(PomodoroState())
    val state: StateFlow<PomodoroState> = _state.asStateFlow()

    private val _focusVisible = MutableStateFlow(false)
    val focusVisible: StateFlow<Boolean> = _focusVisible.asStateFlow()

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
        _state.update {
            if (it.phase == PomodoroPhase.RUNNING) it.copy(phase = PomodoroPhase.PAUSED) else it
        }
    }

    fun resume() {
        _state.update {
            if (it.phase == PomodoroPhase.PAUSED) it.copy(phase = PomodoroPhase.RUNNING) else it
        }
    }

    fun tick(): Boolean {
        var finished = false
        _state.update { current ->
            if (current.phase != PomodoroPhase.RUNNING) {
                current
            } else {
                val remaining = current.remainingSeconds - 1
                if (remaining <= 0) {
                    finished = true
                    current.copy(phase = PomodoroPhase.FINISHED, remainingSeconds = 0)
                } else {
                    current.copy(remainingSeconds = remaining)
                }
            }
        }
        return finished
    }

    fun cancel(): PomodoroState {
        val snapshot = _state.value
        _state.value = PomodoroState()
        _focusVisible.value = false
        return snapshot
    }

    fun finishWithNotice(notice: String) {
        _state.update { it.copy(phase = PomodoroPhase.FINISHED, notice = notice) }
        _focusVisible.value = false
    }

    fun clear() {
        _state.value = PomodoroState()
        _focusVisible.value = false
    }
}
