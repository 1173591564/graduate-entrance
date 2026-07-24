package com.graduateentrance.app.ui

import android.content.Context
import android.graphics.Typeface
import android.view.View
import android.widget.TextView
import com.graduateentrance.app.network.PaperBlockDto
import io.noties.markwon.Markwon
import io.noties.markwon.ext.latex.JLatexMathPlugin
import io.noties.markwon.inlineparser.MarkwonInlineParserPlugin

/** One rendered unit on a page: a heading, or a (possibly split) paragraph fragment. */
internal sealed interface PageItem {
    val blockIndex: Int

    data class Heading(override val blockIndex: Int, val level: Int, val md: String) : PageItem

    data class Paragraph(override val blockIndex: Int, val md: String) : PageItem
}

/**
 * Measures block heights with an off-screen [TextView] configured identically to how the reader
 * renders paragraphs, so pagination matches the real layout. Reused across measurements.
 */
internal class ParagraphMeasurer(
    context: Context,
    private val widthPx: Int,
    fontSizeSp: Float,
    private val lineSpacingMultiplier: Float,
) {
    private val density = context.resources.displayMetrics.scaledDensity
    private val markwon: Markwon = Markwon.builder(context)
        .usePlugin(MarkwonInlineParserPlugin.create())
        .usePlugin(
            JLatexMathPlugin.create(fontSizeSp * density) { builder ->
                builder.inlinesEnabled(true)
            },
        )
        .build()
    private val view = TextView(context).apply {
        textSize = fontSizeSp
        typeface = Typeface.SERIF
        setLineSpacing(0f, lineSpacingMultiplier)
    }
    private val cache = HashMap<String, Int>()

    fun measure(markdown: String): Int = cache.getOrPut(markdown) {
        markwon.setMarkdown(view, normalizeLatexDelimiters(markdown))
        view.measure(
            View.MeasureSpec.makeMeasureSpec(widthPx, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED),
        )
        view.measuredHeight
    }
}

/** Whitespace cut points that do not fall inside a `$...$` / `$$...$$` math span. */
private fun mathSafeBoundaries(md: String): List<Int> {
    val bounds = ArrayList<Int>()
    var index = 0
    var inMath = false
    while (index < md.length) {
        val char = md[index]
        if (char == '$') {
            val double = index + 1 < md.length && md[index + 1] == '$'
            inMath = !inMath
            index += if (double) 2 else 1
            continue
        }
        if (!inMath && char == ' ' && index > 0) {
            bounds.add(index)
        }
        index++
    }
    return bounds
}

/**
 * Splits [md] so the returned prefix fits within [availablePx]. Returns the prefix and the
 * remainder (null when the whole thing fits). An empty prefix means nothing fits the available
 * space and the caller should retry on a fresh page.
 */
private fun splitToFit(
    md: String,
    availablePx: Int,
    measure: (String) -> Int,
): Pair<String, String?> {
    if (measure(md) <= availablePx) return md to null
    val bounds = mathSafeBoundaries(md)
    if (bounds.isEmpty()) return md to null
    var lo = 0
    var hi = bounds.size - 1
    var best = -1
    while (lo <= hi) {
        val mid = (lo + hi) / 2
        if (measure(md.substring(0, bounds[mid])) <= availablePx) {
            best = mid
            lo = mid + 1
        } else {
            hi = mid - 1
        }
    }
    if (best < 0) return "" to md
    val cut = bounds[best]
    return md.substring(0, cut).trim() to md.substring(cut).trim()
}

/**
 * Packs blocks into pages that each fit within [pageHeightPx]. Paragraphs taller than a page are
 * split at word boundaries (never inside a formula); headings are kept whole and never left as the
 * last item on a page.
 */
internal fun paginateBlocks(
    blocks: List<PaperBlockDto>,
    pageHeightPx: Int,
    measureParagraph: (String) -> Int,
    measureHeading: (String, Int) -> Int,
): List<List<PageItem>> {
    if (pageHeightPx <= 0) return listOf(blocks.mapIndexed { index, block -> block.toWholeItem(index) })
    val pages = ArrayList<MutableList<PageItem>>()
    var current = ArrayList<PageItem>()
    var used = 0

    fun flush() {
        if (current.isNotEmpty()) {
            pages.add(current)
            current = ArrayList()
            used = 0
        }
    }

    blocks.forEachIndexed { index, block ->
        if (block.type == "heading") {
            val level = block.level ?: 2
            val height = measureHeading(block.md, level)
            // Avoid orphan headings stranded at the bottom of a page.
            if (used > 0 && used + height > pageHeightPx - pageHeightPx / 6) {
                flush()
            }
            current.add(PageItem.Heading(index, level, block.md))
            used += height
            return@forEachIndexed
        }
        val full = measureParagraph(block.md)
        if (used + full <= pageHeightPx) {
            current.add(PageItem.Paragraph(index, block.md))
            used += full
            return@forEachIndexed
        }
        if (full <= pageHeightPx && used > 0) {
            flush()
            current.add(PageItem.Paragraph(index, block.md))
            used = full
            return@forEachIndexed
        }
        var text = block.md
        while (true) {
            val available = pageHeightPx - used
            val (prefix, rest) = splitToFit(text, available, measureParagraph)
            if (prefix.isEmpty()) {
                if (used > 0) {
                    flush()
                    continue
                }
                val bounds = mathSafeBoundaries(text)
                if (bounds.isEmpty()) {
                    current.add(PageItem.Paragraph(index, text))
                    flush()
                    break
                }
                val cut = bounds[0]
                current.add(PageItem.Paragraph(index, text.substring(0, cut).trim()))
                flush()
                text = text.substring(cut).trim()
                continue
            }
            current.add(PageItem.Paragraph(index, prefix))
            if (rest == null) {
                used += measureParagraph(prefix)
                break
            }
            flush()
            text = rest
        }
    }
    flush()
    return if (pages.isEmpty()) listOf(emptyList()) else pages
}

private fun PaperBlockDto.toWholeItem(index: Int): PageItem =
    if (type == "heading") {
        PageItem.Heading(index, level ?: 2, md)
    } else {
        PageItem.Paragraph(index, md)
    }
