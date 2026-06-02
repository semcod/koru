package com.semcod.koru.autopilot

import com.intellij.openapi.Disposable
import com.intellij.openapi.application.ApplicationInfo
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.Logger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.BufferedReader
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
                startReadLoop(ch)
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

    private fun startReadLoop(ch: SocketChannel) {
        scope.launch {
            runCatching {
                val reader = BufferedReader(
                    Channels.newReader(ch, StandardCharsets.UTF_8.name()),
                )
                while (isActive) {
                    val line = withContext(Dispatchers.IO) { reader.readLine() } ?: break
                    handleIncoming(line.trim())
                }
            }.onFailure { err ->
                if (isActive) log.warn("koru autopilot read loop ended", err)
            }
        }
    }

    private fun handleIncoming(line: String) {
        if (line.isEmpty()) return
        val type = extractJsonString(line, "type") ?: return
        when (type) {
            "chat.send" -> {
                val text = extractJsonString(line, "text") ?: return
                val submit = extractJsonBool(line, "submit") ?: true
                val msgId = extractJsonString(line, "id")
                log.info("koru chat.send: ${text.length} chars, submit=$submit")
                val result = ChatInjector.sendToChat(text, submit = submit)
                val status = if (result.ok) "ok" else "error"
                val replyId = msgId ?: "jetbrains-ack-${UUID.randomUUID()}"
                scope.launch {
                    channel?.let {
                        writeJsonLine(it, buildAck(replyId, status, submit, result))
                        if (result.ok) {
                            writeJsonLine(it, buildMessageSent(text))
                        }
                    }
                }
            }
            else -> log.debug("koru autopilot: unhandled message type=$type")
        }
    }

    private fun buildAck(
        replyId: String,
        status: String,
        submit: Boolean,
        result: ChatInjectResult,
    ): Map<String, Any?> {
        val strictVerified = result.ok &&
            result.focusCommand.isNotBlank() &&
            result.pasteCommand.isNotBlank() &&
            (!submit || result.submitCommand.isNotBlank())
        val trace = mutableListOf<Map<String, Any?>>(
            mapOf(
                "op" to "focus_open",
                "route" to result.focusCommand,
                "ok" to (result.ok && result.focusCommand.isNotBlank()),
            ),
            mapOf(
                "op" to "paste",
                "route" to result.pasteCommand,
                "ok" to result.ok,
            ),
        )
        if (submit) {
            trace.add(
                mapOf(
                    "op" to "submit",
                    "route" to result.submitCommand,
                    "ok" to result.ok,
                ),
            )
        }
        return mapOf(
            "type" to "ack",
            "id" to replyId,
            "ok" to result.ok,
            "status" to status,
            "backend" to "plugin",
            "ide" to "jetbrains",
            "delivered" to result.ok,
            "opened" to result.ok,
            "submitted" to (result.ok && submit),
            "verification" to if (strictVerified && submit) "strict" else "plugin_ack",
            "winning_focus_open" to result.focusCommand,
            "winning_paste" to result.pasteCommand,
            "winning_submit" to if (submit) result.submitCommand else "",
            "attempted_paste" to result.pasteCommand,
            "attempted_submit" to if (submit) result.submitCommand else "",
            "reason" to result.reason,
            "operation_trace" to trace,
        )
    }

    private fun buildMessageSent(text: String): Map<String, Any?> {
        return mapOf(
            "type" to "message.sent",
            "id" to "jetbrains-sent-${UUID.randomUUID()}",
            "chat" to "jetbrains",
            "text" to text,
            "length" to text.length,
        )
    }

    private fun extractJsonString(json: String, key: String): String? {
        val pattern = Regex("\"${Regex.escape(key)}\"\\s*:\\s*\"((?:[^\\\\\"]|\\\\.)*)\"")
        return pattern.find(json)?.groupValues?.get(1)
            ?.replace("\\\\", "\\").replace("\\\"", "\"")
            ?.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
    }

    private fun extractJsonBool(json: String, key: String): Boolean? {
        val pattern = Regex("\"${Regex.escape(key)}\"\\s*:\\s*(true|false)")
        return pattern.find(json)?.groupValues?.get(1)?.let { it == "true" }
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
                "protocolVersion" to 2,
                "capabilities" to listOf("chat.paste", "chat.submit", "chat.events"),
            ),
        )
    }

    private suspend fun writeJsonLine(ch: SocketChannel, payload: Map<String, Any?>) {
        withContext(Dispatchers.IO) {
            val writer = BufferedWriter(
                Channels.newWriter(ch, StandardCharsets.UTF_8.newEncoder(), -1),
            )
            writer.write(toJsonObject(payload))
            writer.newLine()
            writer.flush()
        }
    }

    private fun toJsonObject(payload: Map<String, Any?>): String {
        return payload.entries.joinToString(prefix = "{", postfix = "}") { (key, value) ->
            "\"${escapeJson(key)}\":${toJsonValue(value)}"
        }
    }

    private fun toJsonValue(value: Any?): String {
        return when (value) {
            null -> "null"
            is Number, is Boolean -> value.toString()
            is Map<*, *> -> value.entries.joinToString(prefix = "{", postfix = "}") { entry ->
                "\"${escapeJson(entry.key.toString())}\":${toJsonValue(entry.value)}"
            }
            is Iterable<*> -> value.joinToString(prefix = "[", postfix = "]") { item -> toJsonValue(item) }
            else -> "\"${escapeJson(value.toString())}\""
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
