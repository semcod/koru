package com.semcod.koru.autopilot

import java.nio.file.Path
import kotlin.io.path.absolute

private val SAFE_INSTANCE = Regex("[^A-Za-z0-9_-]+")

fun defaultSocketPath(env: Map<String, String> = System.getenv()): Path {
    env["KORU_AUTOPILOT_SOCKET"]?.trim()?.takeIf { it.isNotEmpty() }?.let {
        return Path.of(it).absolute()
    }

    val instance = env["KORU_AUTOPILOT_INSTANCE"]?.trim().orEmpty()
    val socketName = if (instance.isNotEmpty()) {
        val slug = instance.take(64).replace(SAFE_INSTANCE, "-").trim('-').ifEmpty { "instance" }
        "koru-autopilot-$slug.sock"
    } else {
        "koru-autopilot.sock"
    }

    env["XDG_RUNTIME_DIR"]?.trim()?.takeIf { it.isNotEmpty() }?.let {
        return Path.of(it, socketName)
    }

    val userId = env["UID"]?.trim()?.takeIf { it.isNotEmpty() }
        ?: System.getProperty("user.name", "user")
    val fallbackName = if (socketName == "koru-autopilot.sock") {
        "koru-autopilot-$userId.sock"
    } else {
        socketName.removeSuffix(".sock") + "-$userId.sock"
    }
    return Path.of("/tmp", fallbackName)
}
