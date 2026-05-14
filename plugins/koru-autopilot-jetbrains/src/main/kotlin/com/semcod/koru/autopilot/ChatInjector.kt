package com.semcod.koru.autopilot

/**
 * Placeholder for the JetBrains AI Assistant integration.
 *
 * The first shipped JetBrains slice is the same-UID unix-socket bridge. Actual
 * AI Assistant chat focus, paste/submit, and lifecycle hooks remain isolated
 * here so they can track JetBrains API changes without destabilising the
 * daemon protocol.
 */
class ChatInjector
