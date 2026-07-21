"""Telegram Bot adapter for Hermes Gateway.

Handles incoming Telegram messages, manages sessions, and executes tool_calls
returned by the LLM instead of rendering them as XML/CDATA text.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Optional, Union, List, Dict

from telegram import Update, Bot, Message, User, Chat
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
)

from gateway.platforms.base import (
    BaseAdapter,
    MessageEvent,
    MessageType,
    Platform,
    EphemeralReply,
)
from gateway.session import SessionSource, build_session_key
from hermes_cli.tool_executor import ToolExecutor, ToolResult

logger = logging.getLogger("gateway.telegram")

# Regex patterns for inline tool call formats (Hermes, Qwen, function-calling XML)
INLINE_TOOL_CALL_PATTERNS = [
    # <function=name>{...}</function>  (Hermes style)
    re.compile(r'<function=([a-zA-Z_][a-zA-Z0-9_]*)>\s*(\{.*?\})\s*</function>', re.DOTALL),
    # <tool_call>\n{"name": "...", "arguments": ...}\n</tool_call>  (Qwen style)
    re.compile(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', re.DOTALL),
    # <|tool_call_begin|>...<|tool_call_end|>  (some models)
    re.compile(r'<\|tool_call_begin\|>(.*?)<\|tool_call_end\|>', re.DOTALL),
    # [TOOL_CALLS]...[/TOOL_CALLS] with JSON inside
    re.compile(r'\[TOOL_CALLS\]\s*(\[.*?\])\s*\[/TOOL_CALLS\]', re.DOTALL),
]

def parse_inline_tool_calls(text: str, available_tools: List[Dict] | None = None) -> List[Dict]:
    """Extract structured tool_calls from inline XML/JSON in text content.
    
    Returns list of tool_calls in OpenAI format: {"id": "...", "type": "function", "function": {"name": "...", "arguments": "..."}}
    """
    if not text or not isinstance(text, str):
        return []
    
    tool_names = set()
    if available_tools:
        tool_names = {t.get("function", {}).get("name", "") for t in available_tools}
    
    calls = []
    call_index = 0
    
    for pattern in INLINE_TOOL_CALL_PATTERNS:
        for match in pattern.finditer(text):
            call_index += 1
            try:
                if pattern.pattern.startswith(r'<function='):
                    # Hermes: <function=name>{args}</function>
                    name = match.group(1)
                    args_str = match.group(2).strip()
                elif pattern.pattern.startswith(r'<tool_call>'):
                    # Qwen: <tool_call>{json}</tool_call>
                    json_str = match.group(1).strip()
                    parsed = json.loads(json_str)
                    name = parsed.get("name", "")
                    args_str = json.dumps(parsed.get("arguments", {}), ensure_ascii=False)
                elif pattern.pattern.startswith(r'<\|tool_call_begin\|>'):
                    # Generic: <|tool_call_begin|>json<|tool_call_end|>
                    json_str = match.group(1).strip()
                    parsed = json.loads(json_str)
                    name = parsed.get("name", "")
                    args_str = json.dumps(parsed.get("arguments", {}), ensure_ascii=False)
                elif pattern.pattern.startswith(r'\[TOOL_CALLS\]'):
                    # CDATA wrapper: [TOOL_CALLS][...][/TOOL_CALLS]
                    json_str = match.group(1).strip()
                    parsed = json.loads(json_str)
                    if isinstance(parsed, list):
                        for item in parsed:
                            call_index += 1
                            name = item.get("name", "") or item.get("function", {}).get("name", "")
                            args = item.get("arguments", {}) or item.get("function", {}).get("arguments", {})
                            args_str = json.dumps(args, ensure_ascii=False)
                            if name and (not tool_names or name in tool_names):
                                calls.append({
                                    "id": f"call_inline_{call_index}",
                                    "type": "function",
                                    "function": {"name": name, "arguments": args_str}
                                })
                        continue
                    else:
                        name = parsed.get("name", "") or parsed.get("function", {}).get("name", "")
                        args_str = json.dumps(parsed.get("arguments", {}) or parsed.get("function", {}).get("arguments", {}), ensure_ascii=False)
                else:
                    continue
                
                if name and (not tool_names or name in tool_names):
                    calls.append({
                        "id": f"call_inline_{call_index}",
                        "type": "function",
                        "function": {"name": name, "arguments": args_str}
                    })
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                logger.debug(f"Failed to parse inline tool call: {e}")
                continue
    
    return calls


@dataclass
class TelegramAdapter(BaseAdapter):
    """Telegram Bot API adapter with tool_calls execution support."""

    bot: Bot
    application: Application
    gateway_runner: Any  # GatewayRunner instance
    _pending_tool_calls: Dict[str, List[Dict]] = field(default_factory=dict)
    _tool_executor: Optional[ToolExecutor] = None

    @property
    def platform(self) -> Platform:
        return Platform.TELEGRAM

    @property
    def typed_command_prefix(self) -> str:
        return "/"

    async def start(self) -> None:
        """Start the Telegram bot application."""
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        logger.info("Telegram adapter started")

    async def stop(self) -> None:
        """Stop the Telegram bot application."""
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        logger.info("Telegram adapter stopped")

    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional[str] = "Markdown",
        reply_to_message_id: Optional[int] = None,
        thread_id: Optional[int] = None,
        **kwargs,
    ) -> Message:
        """Send a text message to Telegram."""
        return await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
            message_thread_id=thread_id,
            **kwargs,
        )

    async def send_typing(self, chat_id: Union[int, str], thread_id: Optional[int] = None) -> None:
        """Send typing indicator."""
        await self.bot.send_chat_action(
            chat_id=chat_id,
            action="typing",
            message_thread_id=thread_id,
        )

    def _build_source(self, update: Update) -> SessionSource:
        """Build SessionSource from Telegram update."""
        msg = update.effective_message
        user = update.effective_user
        chat = update.effective_chat

        thread_id = None
        if msg and msg.is_topic_message:
            thread_id = msg.message_thread_id

        return SessionSource(
            platform=Platform.TELEGRAM,
            user_id=str(user.id) if user else "unknown",
            user_name=user.username if user else None,
            chat_id=str(chat.id) if chat else "unknown",
            chat_name=chat.title or chat.username if chat else None,
            chat_type="group" if chat and chat.type in ("group", "supergroup") else "dm",
            thread_id=str(thread_id) if thread_id else None,
            message_id=str(msg.message_id) if msg else None,
        )

    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Main update handler - processes messages and callback queries."""
        if update.callback_query:
            await self._handle_callback_query(update.callback_query)
            return

        msg = update.effective_message
        if not msg or not msg.text:
            return

        source = self._build_source(update)
        text = msg.text.strip()

        # Handle slash commands
        if text.startswith("/"):
            await self._handle_slash_command(source, text, msg.message_id)
            return

        # Regular message - process through gateway
        event = MessageEvent(
            text=text,
            message_type=MessageType.TEXT,
            source=source,
            raw_message=update,
            message_id=msg.message_id,
        )

        # Send typing indicator
        await self.send_typing(source.chat_id, source.thread_id)

        # Process through gateway runner
        try:
            response = await self.gateway_runner._handle_message(event)
            await self._send_response(source, response, msg.message_id)
        except Exception as e:
            logger.exception("Error handling message")
            await self.send_message(
                source.chat_id,
                f"❌ Ошибка: {e}",
                thread_id=source.thread_id,
            )

    async def _handle_slash_command(
        self,
        source: SessionSource,
        text: str,
        message_id: int,
    ) -> None:
        """Handle slash commands via gateway."""
        event = MessageEvent(
            text=text,
            message_type=MessageType.COMMAND,
            source=source,
            message_id=message_id,
        )
        try:
            response = await self.gateway_runner._handle_message(event)
            await self._send_response(source, response, message_id)
        except Exception as e:
            logger.exception("Error handling slash command")
            await self.send_message(
                source.chat_id,
                f"❌ Ошибка команды: {e}",
                thread_id=source.thread_id,
            )

    async def _handle_callback_query(self, callback_query) -> None:
        """Handle inline button callbacks (approvals, confirmations)."""
        await callback_query.answer()
        data = callback_query.data
        source = self._build_source(callback_query)

        # Handle approval callbacks: "approve:<session_key>:<choice>"
        if data.startswith("approve:") or data.startswith("deny:"):
            await self._handle_approval_callback(source, data, callback_query.message.message_id)
        else:
            logger.debug("Unhandled callback: %s", data)

    async def _handle_approval_callback(
        self,
        source: SessionSource,
        data: str,
        message_id: int,
    ) -> None:
        """Process approval/deny callback and resume agent."""
        parts = data.split(":", 2)
        action = parts[0]  # "approve" or "deny"
        session_key = parts[1] if len(parts) > 1 else ""
        choice = parts[2] if len(parts) > 2 else "once"

        # Resolve approval via gateway
        from tools.approval import resolve_gateway_approval
        count = resolve_gateway_approval(session_key, choice, resolve_all=(choice == "all"))

        if count:
            # Resume typing and let agent continue
            await self.send_typing(source.chat_id, source.thread_id)
            # The agent will continue automatically via the approval event
            await self.send_message(
                source.chat_id,
                f"✅ {'Подтверждено' if action == 'approve' else 'Отклонено'} ({count} команд)",
                reply_to_message_id=message_id,
                thread_id=source.thread_id,
            )
        else:
            await self.send_message(
                source.chat_id,
                "⚠️ Нет ожидающих подтверждений",
                reply_to_message_id=message_id,
                thread_id=source.thread_id,
            )

    def _extract_tool_calls(self, response: Any, available_tools: List[Dict] | None = None) -> Optional[List[Dict]]:
        """Универсальное извлечение tool_calls из любого формата ответа gateway_runner.
        
        Поддерживаемые форматы:
        1. Объект с атрибутом .tool_calls
        2. Dict с ключом 'tool_calls'
        3. OpenAI response format: {'choices': [{'message': {'tool_calls': [...]}}]}
        4. EphemeralReply с tool_calls в метаданных
        5. FALLBACK: Parse inline tool calls from content text (XML/JSON formats)
        """
        if response is None:
            return None
        
        # 1. Объект с атрибутом tool_calls
        if hasattr(response, "tool_calls"):
            tool_calls = getattr(response, "tool_calls", None)
            if tool_calls:
                return tool_calls
        
        # 2. Dict с tool_calls
        if isinstance(response, dict):
            # Прямой tool_calls
            if "tool_calls" in response and response["tool_calls"]:
                return response["tool_calls"]
            # OpenAI format
            if "choices" in response:
                try:
                    msg = response["choices"][0].get("message", {})
                    if "tool_calls" in msg and msg["tool_calls"]:
                        return msg["tool_calls"]
                except (IndexError, KeyError, TypeError):
                    pass
        
        # 3. EphemeralReply с tool_calls
        if isinstance(response, EphemeralReply):
            # Проверяем метаданные или атрибуты
            if hasattr(response, "tool_calls") and response.tool_calls:
                return response.tool_calls
            if hasattr(response, "metadata") and isinstance(response.metadata, dict):
                if "tool_calls" in response.metadata and response.metadata["tool_calls"]:
                    return response.metadata["tool_calls"]
        
        # 4. FALLBACK: Parse inline tool calls from content text
        content = self._extract_content(response)
        if content:
            inline_calls = parse_inline_tool_calls(content, available_tools)
            if inline_calls:
                logger.info(f"[Telegram] Rescued {len(inline_calls)} inline tool call(s) from content text")
                return inline_calls
        
        return None

    def _extract_content(self, response: Any) -> str:
        """Универсальное извлечение текстового контента из ответа."""
        if response is None:
            return ""
        
        # EphemeralReply
        if isinstance(response, EphemeralReply):
            return response.message
        
        # Строка
        if isinstance(response, str):
            return response
        
        # Объект с content
        if hasattr(response, "content"):
            content = getattr(response, "content", "")
            if content:
                return str(content)
        
        # Dict с content
        if isinstance(response, dict):
            # Прямой content
            if "content" in response and response["content"]:
                return str(response["content"])
            # OpenAI format
            if "choices" in response:
                try:
                    msg = response["choices"][0].get("message", {})
                    if "content" in msg and msg["content"]:
                        return str(msg["content"])
                except (IndexError, KeyError, TypeError):
                    pass
        
        # Fallback
        return str(response)

    async def _send_response(
        self,
        source: SessionSource,
        response: Union[str, EphemeralReply, None],
        reply_to_message_id: Optional[int] = None,
    ) -> None:
        """Send response to Telegram, handling EphemeralReply and tool_calls."""
        if response is None:
            return

        # Get available tools for inline parsing fallback
        session_key = build_session_key(source)
        session_entry = self.gateway_runner.session_store.get_or_create_session(source)
        available_tools = getattr(session_entry, 'available_tools', None)

        # СНАЧАЛА проверяем tool_calls — они имеют приоритет над текстом
        tool_calls = self._extract_tool_calls(response, available_tools)
        if tool_calls:
            await self._execute_tool_calls_and_respond(source, response, tool_calls, reply_to_message_id)
            return

        # Обычный текстовый ответ
        text = self._extract_content(response)
        if text:
            # Strip any residual inline tool call XML from display text
            text = self._strip_inline_tool_calls(text)
            if text.strip():
                await self.send_message(
                    source.chat_id,
                    text,
                    reply_to_message_id=reply_to_message_id,
                    thread_id=source.thread_id,
                )

    def _strip_inline_tool_calls(self, text: str) -> str:
        """Remove inline tool call XML/JSON from text for clean display."""
        if not text:
            return ""
        cleaned = text
        for pattern in INLINE_TOOL_CALL_PATTERNS:
            cleaned = pattern.sub('', cleaned)
        # Also remove CDATA-style wrappers
        cleaned = re.sub(r'\[TOOL_CALLS\].*?\[/TOOL_CALLS\]', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<!\[CDATA\[.*?\]\]>', '', cleaned, flags=re.DOTALL)
        return cleaned.strip()

    async def _execute_tool_calls_and_respond(
        self,
        source: SessionSource,
        llm_response: Any,
        tool_calls: List[Dict],
        reply_to_message_id: Optional[int],
    ) -> None:
        """Execute tool_calls from LLM response and send final result.

        This is the KEY FIX: instead of rendering tool_calls as XML/CDATA text,
        we execute them via ToolExecutor and feed results back to the LLM.
        If tool_calls cannot be executed, show "Выполняю команду..." as fallback.
        """
        if not tool_calls:
            # No tool calls, just send content
            content = self._extract_content(llm_response)
            content = self._strip_inline_tool_calls(content)
            if content.strip():
                await self.send_message(
                    source.chat_id,
                    content,
                    reply_to_message_id=reply_to_message_id,
                    thread_id=source.thread_id,
                )
            return

        # Initialize tool executor if needed
        if self._tool_executor is None:
            self._tool_executor = ToolExecutor()

        session_key = build_session_key(source)
        session_entry = self.gateway_runner.session_store.get_or_create_session(source)

        # Show progress for tool execution
        progress_msg = await self.send_message(
            source.chat_id,
            f"🔧 Выполняю {len(tool_calls)} инструмент(ов)...",
            reply_to_message_id=reply_to_message_id,
            thread_id=source.thread_id,
        )

        try:
            # Execute all tool calls
            results: List[ToolResult] = []
            for i, tc in enumerate(tool_calls):
                func_name = tc.get("function", {}).get("name", "unknown")
                await self.bot.edit_message_text(
                    chat_id=source.chat_id,
                    message_id=progress_msg.message_id,
                    text=f"🔧 [{i+1}/{len(tool_calls)}] Выполняю `{func_name}`...",
                    parse_mode="Markdown",
                )

                result = await self._tool_executor.execute(
                    tool_call=tc,
                    session_id=session_entry.session_id,
                    gateway_runner=self.gateway_runner,
                    source=source,
                )
                results.append(result)

            # Feed tool results back to LLM for final response
            final_response = await self._get_final_response_after_tools(
                source,
                session_entry,
                tool_calls,
                results,
            )

            # Replace progress message with final response
            await self.bot.edit_message_text(
                chat_id=source.chat_id,
                message_id=progress_msg.message_id,
                text=final_response,
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.exception("Tool execution failed")
            # Если tool_calls нельзя выполнить — заменяем на текст "Выполняю команда..."
            await self.bot.edit_message_text(
                chat_id=source.chat_id,
                message_id=progress_msg.message_id,
                text="Выполняю команду...",
                parse_mode="Markdown",
            )

    async def _get_final_response_after_tools(
        self,
        source: SessionSource,
        session_entry: Any,
        tool_calls: List[Dict],
        results: List[ToolResult],
    ) -> str:
        """Send tool results to LLM and get final natural language response."""
        # Build tool result messages for the LLM
        tool_messages = []
        for tc, result in zip(tool_calls, results):
            tool_messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id"),
                "name": tc.get("function", {}).get("name"),
                "content": result.output if result.success else f"Error: {result.error}",
            })

        # Get the agent for this session to continue the conversation
        session_key = build_session_key(source)
        agent = self.gateway_runner._running_agents.get(session_key)

        if agent and hasattr(agent, "continue_with_tool_results"):
            # Agent supports continuing with tool results
            final = await agent.continue_with_tool_results(tool_messages)
            return final.get("content", "Готово") if isinstance(final, dict) else str(final)

        # Fallback: summarize results
        lines = ["✅ Инструменты выполнены:"]
        for tc, result in zip(tool_calls, results):
            name = tc.get("function", {}).get("name", "unknown")
            status = "✅" if result.success else "❌"
            lines.append(f"  {status} `{name}`")
            if not result.success and result.error:
                lines.append(f"     Ошибка: {result.error}")
        return "\n".join(lines)

    def register_handlers(self) -> None:
        """Register Telegram update handlers."""
        self.application.add_handler(
            MessageHandler(filters.ALL & ~filters.COMMAND, self._handle_update)
        )
        self.application.add_handler(
            CommandHandler("start", self._handle_update)
        )
        self.application.add_handler(
            CallbackQueryHandler(self._handle_callback_query)
        )


async def create_telegram_adapter(gateway_runner: Any) -> TelegramAdapter:
    """Factory function to create and configure Telegram adapter."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")

    bot = Bot(token=token)
    application = ApplicationBuilder().bot(bot).build()

    adapter = TelegramAdapter(
        bot=bot,
        application=application,
        gateway_runner=gateway_runner,
    )

    adapter.register_handlers()
    return adapter
