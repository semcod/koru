package com.semcod.koru.autopilot

import com.intellij.openapi.Disposable
import com.intellij.openapi.application.ApplicationInfo
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.Logger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.BufferedWriter
import java.net.StandardProtocolFamily
import java.nio.channels.Channels
import java.nio.channels.SocketChannel
import java.nio.charset.StandardCharsets
import java.nio.file.Path
import java.util.UUID
import kotlin.io.path.exists

class KoruAutopilotService : Disposable {
    private val log = Logger.getInstance(KoruAutopilotService::class.java)
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    @Volatile private var channel: SocketChannel? = null

    init {
        reconnect()
    }

    fun reconnect(socketPath: Path = defaultSocketPath()) {
        scope.launch {
            disconnect()
            if (!socketPath.exists()) {
                log.info("koru autopilot socket not found: $socketPath")
                return@launch
            }

            runCatching {
                val socketAddress = Class
                    .forName("java.net.UnixDomainSocketAddress")
                    .getMethod("of", Path::class.java)
                    .invoke(null, socketPath)
                val ch = SocketChannel.open(StandardProtocolFamily.UNIX)
                ch.connect(socketAddress as java.net.SocketAddress)
                channel = ch
                sendHello(ch)
            }.onFailure { err ->
                log.warn("Failed to connect to koru autopilot daemon at $socketPath", err)
            }
        }
    }

    fun sendSessionEnded(reason: String = "manual", chat: String = "jetbrains") {
        val ch = channel ?: return
        scope.launch {
            writeJsonLine(
                ch,
                mapOf(
                    "type" to "session.ended",
                    "id" to "jetbrains-${UUID.randomUUID()}",
                    "chat" to chat,
                    "reason" to reason,
                ),
            )
        }
    }

    private suspend fun disconnect() {
        withContext(Dispatchers.IO) {
            channel?.close()
            channel = null
        }
    }

    private suspend fun sendHello(ch: SocketChannel) {
        val appInfo = ApplicationInfo.getInstance()
        writeJsonLine(
            ch,
            mapOf(
                "type" to "hello",
                "id" to "jetbrains-hello",
                "ide" to "jetbrains",
                "version" to appInfo.fullVersion,
                "pid" to ProcessHandle.current().pid(),
            ),
        )
    }

    private suspend fun writeJsonLine(ch: SocketChannel, payload: Map<String, Any>) {
        withContext(Dispatchers.IO) {
            val writer = BufferedWriter(
                Channels.newWriter(ch, StandardCharsets.UTF_8.newEncoder(), -1),
            )
            writer.write(toJsonObject(payload))
            writer.newLine()
            writer.flush()
        }
    }

    private fun toJsonObject(payload: Map<String, Any>): String {
        return payload.entries.joinToString(prefix = "{", postfix = "}") { (key, value) ->
            val encodedValue = when (value) {
                is Number, is Boolean -> value.toString()
                else -> "\"${escapeJson(value.toString())}\""
            }
            "\"${escapeJson(key)}\":$encodedValue"
        }
    }

    private fun escapeJson(raw: String): String = buildString(raw.length) {
        for (ch in raw) {
            when (ch) {
                '\\' -> append("\\\\")
                '"' -> append("\\\"")
                '\b' -> append("\\b")
                '\u000C' -> append("\\f")
                '\n' -> append("\\n")
                '\r' -> append("\\r")
                '\t' -> append("\\t")
                else -> append(ch)
            }
        }
    }

    override fun dispose() {
        runCatching { channel?.close() }
        channel = null
        scope.cancel()
    }

    companion object {
        fun getInstance(): KoruAutopilotService =
            ApplicationManager.getApplication().getService(KoruAutopilotService::class.java)
    }
}
