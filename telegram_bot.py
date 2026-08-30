"""Telegram gateway for worker updates, voice notes, documents, and grounded questions."""

from __future__ import annotations

import os

import agent
import meridian as m


def _allowed(user_id: int) -> bool:
    configured = {x.strip() for x in os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").split(",") if x.strip()}
    return str(user_id) in configured or os.getenv("TELEGRAM_ALLOW_ALL_FOR_DEMO") == "1"


def _actor(update) -> str:
    user = update.effective_user
    return f"telegram:{user.id}:{user.full_name}" if user else "telegram:unknown"


async def _reject(update) -> bool:
    if update.effective_user and _allowed(update.effective_user.id):
        return False
    await update.effective_message.reply_text("This bot is private. Ask operations to add your Telegram user ID.")
    return True


def _format_answer(result: dict) -> str:
    text = f"{result['headline']}\n\n{result.get('detail', '')}".strip()
    if result.get("unknowns"):
        text += "\n\nUnknown / verify now:\n• " + "\n• ".join(result["unknowns"])
    if result.get("extras"):
        text += "\n\nAlso useful:\n• " + "\n• ".join(result["extras"])
    if result.get("citations"):
        text += "\n\nSources: " + " · ".join(result["citations"])
    return text[:4000]


async def start(update, context) -> None:
    if await _reject(update):
        return
    await update.message.reply_text(
        "Namaste. Send a question, ground update, voice note, or document. "
        "I will answer from approved context, or log/stage new evidence for review. I never silently rewrite company truth."
    )


async def handle_text(update, context) -> None:
    if await _reject(update):
        return
    await _process_text(update, update.message.text.strip())


async def _process_text(update, text: str) -> None:
    conn = m.ensure_db()
    result = agent.ingest_text(conn, text, actor=_actor(update), channel="telegram_text", source_ref=f"telegram:{update.message.message_id}")
    if "answer" in result["dispositions"]:
        await update.message.reply_text(_format_answer(agent.ask(conn, text)))
    elif "urgent_escalation" in result["dispositions"]:
        await update.message.reply_text("⚠️ Logged as urgent and staged for operations approval. If anyone is in danger, contact emergency/operations channels now. Ref: " + result["run_id"])
    elif result["proposal_ids"]:
        await update.message.reply_text("Update logged and staged for human approval. Ref: " + ", ".join(result["proposal_ids"]))
    else:
        await update.message.reply_text("Update preserved in the event log; it was not promoted into reusable context. Ref: " + result["run_id"])


async def handle_voice(update, context) -> None:
    if await _reject(update):
        return
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    data = bytes(await file.download_as_bytearray())
    await update.message.reply_text("Voice received—listening and reconciling it with company context…")
    try:
        transcript = agent.transcribe_audio(data, voice.mime_type or "audio/ogg")
    except Exception as exc:
        await update.message.reply_text(f"I could not transcribe this note: {exc}")
        return
    await update.message.reply_text("Transcript: " + transcript[:1200])
    await _process_text(update, transcript)


async def handle_document(update, context) -> None:
    if await _reject(update):
        return
    document = update.message.document
    if document.file_size and document.file_size > 20 * 1024 * 1024:
        await update.message.reply_text("That exceeds Telegram's standard 20 MB bot download limit. Upload it in the Synchus app instead.")
        return
    file = await context.bot.get_file(document.file_id)
    data = bytes(await file.download_as_bytearray())
    try:
        result = agent.ingest_upload(conn=m.ensure_db(), name=document.file_name or "telegram-upload", data=data, media_type=document.mime_type or "", actor=_actor(update))
    except Exception as exc:
        await update.message.reply_text(f"I could not process that document: {exc}")
        return
    if result.get("duplicate"):
        await update.message.reply_text("Already processed—no duplicate context was created.")
    else:
        await update.message.reply_text(f"Document processed. {len(result.get('proposal_ids', []))} claim(s) staged for approval. Ref: {result['run_id']}")


def main() -> None:
    try:
        from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
    except ImportError:
        raise SystemExit("Install Telegram dependencies: uv sync --extra telegram")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN first")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
