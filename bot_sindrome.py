import os
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

# --- DUMMY WEB SERVER (Unlocks Render Free Tier) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Syndrome is online and operational.")

def start_dummy_server():
    port = int(os.getenv("PORT", 8080))
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

def generate_response(user_message: str) -> str:
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.85,
    )
    return chat_completion.choices[0].message.content

async def post_to_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = " ".join(context.args)
    if not user_prompt:
        await update.message.reply_text("Give me a topic or situation to monologue about! E.g.: /post My new Omnidroid upgrade")
        return

    request_prompt = f"Write a public channel post about this topic/situation: {user_prompt}"
    syndrome_response = generate_response(request_prompt)

    await context.bot.send_message(chat_id=CHANNEL_ID, text=syndrome_response)
    await update.message.reply_text("Dispatched to the channel, sweetheart.")

async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    user_first_name = update.effective_user.first_name

    bot_username = context.bot.username
    is_private_chat = update.message.chat.type == "private"
    is_mentioned = f"@{bot_username}" in text or (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user.id == context.bot.id
    )

    if is_private_chat or is_mentioned:
        cleaned_text = text.replace(f"@{bot_username}", "").strip()
        formatted_input = f"[{user_first_name} said]: {cleaned_text}"
        
        response = generate_response(formatted_input)
        await update.message.reply_text(response)

def main():
    # Start web server thread for Render health checks
    threading.Thread(target=start_dummy_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("post", post_to_channel_command))
    app.add_handler(CommandHandler("postar", post_to_channel_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_mention))

    print("Syndrome is online and operational...")
    app.run_polling()

if __name__ == "__main__":
    main()
