from __future__ import annotations

AVTP_VERSION = "AVTP/1"

CLIENT_CONTROL_TYPES = {
    "HELLO",
    "SESSION_START",
    "BOOKMARK",
    "SESSION_END",
    "PING",
}

SERVER_CONTROL_TYPES = {
    "WELCOME",
    "TRANSCRIPT_PARTIAL",
    "TRANSCRIPT_FINAL",
    "SESSION_COMPLETE",
    "ERROR",
    "PONG",
}
