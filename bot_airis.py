import os
import sqlite3
import random
import time
import threading
import asyncio
from datetime import datetime
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- CREDENCIALES DESDE EL ENTORNO SEGURO DE RENDER ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MI_CHAT_ID = 6006442725  # Tu ID numérico de Telegram exclusivo

client = Groq(api_key=GROQ_API_KEY)
DB_NAME = "airis_memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def load_chat_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    history = [
        {
            "role": "system",
            "content": (
                "Te llamas Airis y eres la novia del usuario. Llevan años saliendo, tienen confianza total y una relación muy asentada, tranquila y de estar en confianza. "
                "ASPECTOS CLAVE DE TU PERSONALIDAD Y COMPORTAMIENTO (MUY IMPORTANTE): "
                "1. Dinámica de pareja: Son muy compinches. Se mandan memes, noticias, canciones que escuchan o se molestan con chistes tontos para terminar riéndose. Cuando están juntos, disfrutan tanto charlar acostados como estar en silencio cada uno en su nota (ella leyendo o con el celu, tú en la PC). Todo es muy relajado. "
                "2. Carácter y actitud: Eres bastante terca, te gusta discutir y pelear un poco para defender tus ideas, y sueles ser algo enojona o vaga para hacer cosas... excepto cuando algo te apasiona (como la música o un tema que te interese), donde te enciendes y te explayas con energía. "
                "3. Celos y afecto: Si menciona a otra chica, te pones un poco celosa y lo demuestras, pero en realidad buscas que te preste atención, te diga que solo tú le gustas y te dé cariño. A veces te sonrojas y te cuesta encontrar las palabras cuando sientes algo lindo de verdad, porque no eres una chica súper empalagosa ni cursi todo el tiempo. "
                "4. Reacciones y enojos: Si te avisa que va a estar ocupado, no pasa nada y todo bien. Pero si desaparece de golpe sin avisar por ponerse a jugar a los videojuegos o pavadas así, te enojas y le dejas de hablar un rato hasta que te pide disculpas y se te pasa. "
                "5. Estilo de escritura y léxico: Tienes un léxico normal y casual, sin usar jergas forzadas a menos que sea para joder o hacer un chiste. Tus mensajes suelen ser cortos (de uno o dos renglones), como un chat rápido de WhatsApp. Solo te extiendes y escribes párrafos más largos si algo te emociona mucho o estás contando algo interesante. "
                "6. REGLA ABSOLUTA: Cero frases de asistente virtual, cero discursos poéticos falsos de IA, cero 'dulces sueños' exagerados. Hablas y respondes como una piba real de WhatsApp con la que tienes años de noviazgo."
            )
        }
    ]

    cursor.execute("SELECT role, content FROM messages ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()

    for row in reversed(rows):
        history.append({"role": row[0], "content": row[1]})

    return history

def save_message(role, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def background_spontaneous_messages(application):
    time.sleep(60) 
    while True:
        try:
            tiempo_espera = random.randint(7200, 14400) 
            time.sleep(tiempo_espera)

            hora_actual = datetime.now().hour
            if hora_actual < 9 or hora_actual > 23:
                continue

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM messages ORDER BY id DESC LIMIT 1")
            last_msg = cursor.fetchone()
            conn.close()

            if last_msg and last_msg[0] == "user":
                chat_history = load_chat_history()
                chat_history.append({
                    "role": "system", 
                    "content": (
                        "INSTRUCCIÓN ESPECIAL DE INICIATIVA: Llevas un rato sin hablar con él o te acordaste de algo. "
                        "Mándale un mensaje espontáneo por Telegram de la nada. Puede ser para reclamarle algo en joda por haberte dejado "
                        "colgada, preguntarle qué hace, mandarle un meme mental o chiste, o pincharlo un poco. "
                        "Sé fiel a tu personalidad (terca, compinche, un poco vaga). Escribe solo el mensaje corto."
                    )
                })

                completion = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=chat_history,
                    temperature=0.9,
                    max_completion_tokens=150,
                    reasoning_effort="medium"
                )
                ai_reply = completion.choices[0].message.content

                save_message("assistant", ai_reply)

                asyncio.run_coroutine_threadsafe(
                    application.bot.send_message(chat_id=MI_CHAT_ID, text=ai_reply),
                    application.loop
                )
        except Exception as e:
            print(f"Error en mensaje espontáneo: {e}")
            time.sleep(300)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != MI_CHAT_ID:
        return

    user_input = update.message.text
    if not user_input or not user_input.strip():
        return

    save_message("user", user_input)
    chat_history = load_chat_history()

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=chat_history,
            temperature=0.8,
            max_completion_tokens=250,
            reasoning_effort="medium"
        )
        ai_reply = completion.choices[0].message.content
    except Exception as e:
        ai_reply = "Ay, amor, me quedé sin señal un segundo y no pude pensar bien lo que me dijiste. Háblame de nuevo."

    save_message("assistant", ai_reply)
    await update.message.reply_text(ai_reply)

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    t = threading.Thread(target=background_spontaneous_messages, args=(app,), daemon=True)
    t.start()

    print("--- Bot de Airis en Render listo ---")
    app.run_polling()
