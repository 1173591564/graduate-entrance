package com.graduateentrance.app

import com.graduateentrance.app.ui.normalizeLatexDelimiters
import org.junit.Assert.assertEquals
import org.junit.Test

class MarkdownTextTest {
    @Test
    fun wrapsSingleDollarInlineMathToDouble() {
        assertEquals(
            "极限 \$\$\\lim_{x\\to 0}\\frac{\\sin x}{x}=1\$\$ 成立",
            normalizeLatexDelimiters("极限 \$\\lim_{x\\to 0}\\frac{\\sin x}{x}=1\$ 成立"),
        )
    }

    @Test
    fun keepsDoubleDollarBlocksUnchanged() {
        val block = "\$\$e^x=1+x\$\$"
        assertEquals(block, normalizeLatexDelimiters(block))
    }

    @Test
    fun leavesPlainTextUnchanged() {
        assertEquals("没有公式的内容", normalizeLatexDelimiters("没有公式的内容"))
    }
}
