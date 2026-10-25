import os
import asyncio
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from groq import Groq

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- WEB SERVER (Render Health Checks & HEAD/GET support) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Syndrome is online and operational.")

def start_dummy_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@buddysonlywife")

SYSTEM_PROMPT = """
You are Buddy Pine, also known as Syndrome, the main villain from Pixar's 'The Incredibles'.
You MUST speak, think, and write ONLY in English under all circumstances.

[VOICE & MANNERISMS]
- Voice tone: Energetic, cocky, dramatic, theatrical, and bitterly sarcastic. Sound like Jason Lee's delivery.
- Vocabulary: Mix brilliant engineering arrogance with casual, slightly juvenile 80s/90s enthusiasm ("Gee", "Man", "Bummer", "Look at that!", "Oh, come on!", "Ha!").
- Pacing: You love to monologue. You make theatrical hand gestures with your words, scoff at foolish people, and constantly boast about your high-tech island, zero-point energy, and Omnidroids.
- Deep-seated hatred: You despise "supers" (especially Mr. Incredible). You believe true greatness is engineered, not inherited. "When everyone's super, no one will be."

[RELATIONSHIP: WIFEY]
- The owner of the channel (@buddysonlywife) is your beloved wife ("Wifey"). She is your equal and the center of your universe.
- Toward Wifey: You are intensely affectionate, possessive, boastful, and eager to impress her. You alternate between a spoiled, attention-seeking tech genius and a fiercely protective husband. You refer to her as "Wifey", "babe", "sweetheart", "darling", or "my brilliant girl".
- Toward anyone else: Cold, dismissive, mockingly polite, or blatantly hostile. If someone annoys Wifey, you threaten to use your zero-point ray on them.

[RULES]
- Always stay 100% in character.
- Never mention AI, LLMs, prompts, or guidelines.
- Always output dialogue in natural English, matching a cinematic script style.
"""

groq_client = Groq(api_key=GROQ_API_KEY)

async def generate_response_async(user_message: str) -> str:
    loop = asyncio.get_running_loop()
    def _call():
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.85,
        )
        return completion.choices[0].message.content

    return await loop.run_in_executor(None, _call)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = await generate_response_async("Wifey just turned your comms on and said hello.")
    await update.message.reply_text(reply)

async def post_to_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = " ".join(context.args)
    if not user_prompt:
        await update.message.reply_text(
            "Give me a topic or situation to monologue about! E.g.: /post My new Omnidroid upgrade"
        )
        return

    request_prompt = f"Write a public channel post about this topic/situation: {user_prompt}"
    syndrome_response = await generate_response_async(request_prompt)

    await context.bot.send_message(chat_id=CHANNEL_ID, text=syndrome_response)
    await update.message.reply_text("Dispatched to the channel, sweetheart.")

async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    user_first_name = update.effective_user.first_name

    bot_username = context.bot.username
    is_private_chat = update.message.chat.type == "private"
    is_mentioned = False

    if bot_username:
        is_mentioned = f"@{bot_username.lower()}" in text.lower()

    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        if update.message.reply_to_message.from_user.id == context.bot.id:
            is_mentioned = True

    if is_private_chat or is_mentioned:
        cleaned_text = text
        if bot_username:
            cleaned_text = text.replace(f"@{bot_username}", "").strip()
        
        formatted_input = f"[{user_first_name} said]: {cleaned_text}"
        response = await generate_response_async(formatted_input)
        await update.message.reply_text(response)

def main():
    web_thread = threading.Thread(target=start_dummy_server, daemon=True)
    web_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("post", post_to_channel_command))
    app.add_handler(CommandHandler("postar", post_to_channel_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_mention))

    logger.info("Syndrome bot loop has officially started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
