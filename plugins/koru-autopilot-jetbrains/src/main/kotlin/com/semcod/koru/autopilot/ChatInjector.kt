package com.semcod.koru.autopilot

import com.intellij.openapi.actionSystem.ActionManager
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.DataContext
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.Logger
import java.awt.Toolkit
import java.awt.datatransfer.StringSelection
import java.awt.event.KeyEvent

/**
 * Injects text into the JetBrains AI Assistant chat input.
 *
 * Strategy:
 * 1. Open the AI Assistant tool window via ActionManager.
 * 2. Place the text on the system clipboard.
 * 3. Send Ctrl+V (paste) + optionally Enter (submit) via AWT Robot.
 */
object ChatInjector {
    private val log = Logger.getInstance(ChatInjector::class.java)

    private val AI_OPEN_ACTIONS = listOf(
        "AIAssistant.OpenAIAssistantToolWindow",
        "AIAssistant.Chat.OpenChat",
        "AiAssistant.OpenAiAssistantToolWindow",
        "Grazie.OpenAssistant",
    )

    fun sendToChat(text: String, submit: Boolean = true): Boolean {
        return try {
            ApplicationManager.getApplication().invokeLater {
                openAiPanel()
                pasteViaClipboard(text, submit)
            }
            true
        } catch (e: Exception) {
            log.warn("ChatInjector.sendToChat failed", e)
            false
        }
    }

    private fun openAiPanel() {
        val am = ActionManager.getInstance()
        for (actionId in AI_OPEN_ACTIONS) {
            val action = am.getAction(actionId) ?: continue
            val event = AnActionEvent.createFromAnAction(action, null, "koru", DataContext.EMPTY_CONTEXT)
            action.actionPerformed(event)
            log.info("ChatInjector: opened AI panel via action $actionId")
            Thread.sleep(300)
            return
        }
        log.warn("ChatInjector: no AI Assistant open-action found; tried $AI_OPEN_ACTIONS")
    }

    private fun pasteViaClipboard(text: String, submit: Boolean) {
        val clipboard = Toolkit.getDefaultToolkit().systemClipboard
        clipboard.setContents(StringSelection(text), null)
        Thread.sleep(100)

        val robot = java.awt.Robot()
        robot.keyPress(KeyEvent.VK_CONTROL)
        robot.keyPress(KeyEvent.VK_V)
        robot.keyRelease(KeyEvent.VK_V)
        robot.keyRelease(KeyEvent.VK_CONTROL)

        if (submit) {
            Thread.sleep(50)
            robot.keyPress(KeyEvent.VK_ENTER)
            robot.keyRelease(KeyEvent.VK_ENTER)
        }
        log.info("ChatInjector: pasted ${text.length} chars via clipboard, submit=$submit")
    }
}
