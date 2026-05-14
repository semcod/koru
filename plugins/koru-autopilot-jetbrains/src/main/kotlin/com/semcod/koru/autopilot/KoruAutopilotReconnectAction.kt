package com.semcod.koru.autopilot

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent

class KoruAutopilotReconnectAction : AnAction() {
    override fun actionPerformed(event: AnActionEvent) {
        KoruAutopilotService.getInstance().reconnect()
    }
}
