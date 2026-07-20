package com.graduateentrance.app

import com.graduateentrance.app.timer.PomodoroPhase
import com.graduateentrance.app.timer.PomodoroTimer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class PomodoroTimerTest {
    private var now: Long = 0

    @Before
    fun reset() {
        now = 0
        PomodoroTimer.clock = { now }
        PomodoroTimer.clear()
    }

    @After
    fun tearDown() {
        PomodoroTimer.clear()
    }

    private fun advance(seconds: Long) {
        now += seconds * 1000
    }

    @Test
    fun `start initializes running countdown`() {
        assertTrue(PomodoroTimer.start("task-1", "高数极限", 25))
        val state = PomodoroTimer.state.value
        assertEquals(PomodoroPhase.RUNNING, state.phase)
        assertEquals(25 * 60, state.remainingSeconds)
        assertEquals("task-1", state.taskId)
    }

    @Test
    fun `start rejects when session active or minutes invalid`() {
        assertFalse(PomodoroTimer.start("task-1", "高数极限", 0))
        assertTrue(PomodoroTimer.start("task-1", "高数极限", 25))
        assertFalse(PomodoroTimer.start("task-2", "408", 25))
    }

    @Test
    fun `sync counts down only while running and finishes at zero`() {
        PomodoroTimer.start("task-1", "高数极限", 1)
        advance(1)
        assertFalse(PomodoroTimer.sync())
        assertEquals(59, PomodoroTimer.state.value.remainingSeconds)

        PomodoroTimer.pause()
        advance(30)
        assertFalse(PomodoroTimer.sync())
        assertEquals(59, PomodoroTimer.state.value.remainingSeconds)

        PomodoroTimer.resume()
        advance(58)
        assertFalse(PomodoroTimer.sync())
        assertEquals(1, PomodoroTimer.state.value.remainingSeconds)
        advance(1)
        assertTrue(PomodoroTimer.sync())
        val state = PomodoroTimer.state.value
        assertEquals(PomodoroPhase.FINISHED, state.phase)
        assertEquals(0, state.remainingSeconds)
        assertEquals(1, state.elapsedMinutes)
    }

    @Test
    fun `sync recovers real elapsed time after process throttling`() {
        PomodoroTimer.start("task-1", "高数极限", 25)
        // 模拟系统冻结进程 10 分钟后才再次 sync
        advance(600)
        assertFalse(PomodoroTimer.sync())
        assertEquals(15 * 60, PomodoroTimer.state.value.remainingSeconds)

        // 冻结跨过结束点时直接完成
        advance(20 * 60)
        assertTrue(PomodoroTimer.sync())
        assertEquals(PomodoroPhase.FINISHED, PomodoroTimer.state.value.phase)
    }

    @Test
    fun `cancel returns snapshot and resets state`() {
        PomodoroTimer.start("task-1", "高数极限", 25)
        advance(120)
        val snapshot = PomodoroTimer.cancel()
        assertEquals(2, snapshot.elapsedMinutes)
        assertEquals(PomodoroPhase.IDLE, PomodoroTimer.state.value.phase)
    }

    @Test
    fun `finishWithNotice keeps notice for ui`() {
        PomodoroTimer.start("task-1", "高数极限", 1)
        advance(60)
        PomodoroTimer.sync()
        PomodoroTimer.finishWithNotice("番茄钟完成，已自动打卡 1 分钟")
        assertEquals("番茄钟完成，已自动打卡 1 分钟", PomodoroTimer.state.value.notice)
    }
}
