package com.graduateentrance.app.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import com.graduateentrance.app.data.CaptureImage
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private const val MAX_CAPTURE_EDGE = 1600
private const val CAPTURE_JPEG_QUALITY = 88

suspend fun loadCaptureImage(context: Context, uri: Uri): CaptureImage? =
    withContext(Dispatchers.IO) {
        try {
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            context.contentResolver.openInputStream(uri)?.use {
                BitmapFactory.decodeStream(it, null, bounds)
            }
            if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
                return@withContext null
            }

            var sampleSize = 1
            while (maxOf(bounds.outWidth, bounds.outHeight) / sampleSize > MAX_CAPTURE_EDGE * 2) {
                sampleSize *= 2
            }
            val decoded = context.contentResolver.openInputStream(uri)?.use {
                BitmapFactory.decodeStream(
                    it,
                    null,
                    BitmapFactory.Options().apply { inSampleSize = sampleSize },
                )
            } ?: return@withContext null

            val longestEdge = maxOf(decoded.width, decoded.height)
            val output = if (longestEdge > MAX_CAPTURE_EDGE) {
                val scale = MAX_CAPTURE_EDGE.toFloat() / longestEdge
                Bitmap.createScaledBitmap(
                    decoded,
                    (decoded.width * scale).toInt(),
                    (decoded.height * scale).toInt(),
                    true,
                ).also { decoded.recycle() }
            } else {
                decoded
            }

            val bytes = ByteArrayOutputStream().use { stream ->
                output.compress(Bitmap.CompressFormat.JPEG, CAPTURE_JPEG_QUALITY, stream)
                stream.toByteArray()
            }
            output.recycle()
            CaptureImage(bytes, "image/jpeg")
        } catch (_: Exception) {
            null
        }
    }
