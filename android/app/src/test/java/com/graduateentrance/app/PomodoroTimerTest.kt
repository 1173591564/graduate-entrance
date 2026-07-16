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
    @Before
    fun reset() {
        PomodoroTimer.clear()
    }

    @After
    fun tearDown() {
        PomodoroTimer.clear()
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
    fun `tick counts down only while running and finishes at zero`() {
        PomodoroTimer.start("task-1", "高数极限", 1)
        assertFalse(PomodoroTimer.tick())
        assertEquals(59, PomodoroTimer.state.value.remainingSeconds)

        PomodoroTimer.pause()
        assertFalse(PomodoroTimer.tick())
        assertEquals(59, PomodoroTimer.state.value.remainingSeconds)

        PomodoroTimer.resume()
        repeat(58) {
            assertFalse(PomodoroTimer.tick())
        }
        assertTrue(PomodoroTimer.tick())
        val state = PomodoroTimer.state.value
        assertEquals(PomodoroPhase.FINISHED, state.phase)
        assertEquals(0, state.remainingSeconds)
        assertEquals(1, state.elapsedMinutes)
    }

    @Test
    fun `cancel returns snapshot and resets state`() {
        PomodoroTimer.start("task-1", "高数极限", 25)
        repeat(120) { PomodoroTimer.tick() }
        val snapshot = PomodoroTimer.cancel()
        assertEquals(2, snapshot.elapsedMinutes)
        assertEquals(PomodoroPhase.IDLE, PomodoroTimer.state.value.phase)
    }

    @Test
    fun `finishWithNotice keeps notice for ui`() {
        PomodoroTimer.start("task-1", "高数极限", 1)
        repeat(60) { PomodoroTimer.tick() }
        PomodoroTimer.finishWithNotice("番茄钟完成，已自动打卡 1 分钟")
        assertEquals("番茄钟完成，已自动打卡 1 分钟", PomodoroTimer.state.value.notice)
    }
}
