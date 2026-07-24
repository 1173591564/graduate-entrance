package com.graduateentrance.app.ui

import android.content.Context
import android.graphics.Typeface
import android.widget.TextView
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.isSpecified
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.viewinterop.AndroidView
import io.noties.markwon.Markwon
import io.noties.markwon.ext.latex.JLatexMathPlugin
import io.noties.markwon.inlineparser.MarkwonInlineParserPlugin

private val singleDollarLatex = Regex("(?<!\\$)\\$(?!\\$)([^$\\n]+?)\\$(?!\\$)")

internal fun normalizeLatexDelimiters(markdown: String): String =
    markdown.replace(singleDollarLatex) { match -> "\$\$" + match.groupValues[1] + "\$\$" }

private fun buildMarkwon(context: Context, textSizePx: Float): Markwon =
    Markwon.builder(context)
        .usePlugin(MarkwonInlineParserPlugin.create())
        .usePlugin(
            JLatexMathPlugin.create(textSizePx) { builder ->
                builder.inlinesEnabled(true)
            },
        )
        .build()

@Composable
fun MarkdownText(
    markdown: String,
    modifier: Modifier = Modifier,
    style: TextStyle = LocalTextStyle.current,
    serif: Boolean = false,
    lineSpacingMultiplier: Float = 1f,
    justify: Boolean = false,
    onLongClick: (() -> Unit)? = null,
) {
    val context = LocalContext.current
    val textColor = if (style.color.isSpecified) {
        style.color
    } else {
        MaterialTheme.colorScheme.onSurface
    }
    val density = context.resources.displayMetrics.scaledDensity
    val fontSizeSp = if (style.fontSize != TextUnit.Unspecified) style.fontSize.value else 14f
    val textSizePx = fontSizeSp * density
    AndroidView(
        modifier = modifier,
        factory = { ctx ->
            TextView(ctx).apply {
                setTextIsSelectable(onLongClick == null)
            }
        },
        update = { view ->
            view.textSize = fontSizeSp
            view.setTextColor(textColor.toArgb())
            view.typeface = if (serif) Typeface.SERIF else Typeface.DEFAULT
            view.setLineSpacing(0f, lineSpacingMultiplier)
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                view.justificationMode = if (justify) {
                    android.text.Layout.JUSTIFICATION_MODE_INTER_WORD
                } else {
                    android.text.Layout.JUSTIFICATION_MODE_NONE
                }
            }
            if (onLongClick != null) {
                view.setOnLongClickListener {
                    onLongClick()
                    true
                }
            }
            buildMarkwon(view.context, textSizePx)
                .setMarkdown(view, normalizeLatexDelimiters(markdown))
        },
    )
}
