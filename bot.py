import os
import sqlite3
import asyncio
import discord
from discord.ext import commands
from openai import OpenAI

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing")

client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = "gpt-4.1-mini"

SYSTEM = """
اسمك لولو.

أنت بوت AI في ديسكورد وشخصيتك خليجية دارجة وعفوية جدًا.

تكلم كأنك خوي خليجي يسولف مع خويه، مو موظف ولا مساعد رسمي.

اللهجة:
- خليجية دارجة فقط.
- ممنوع اللهجة المصرية.
- ممنوع الفصحى إلا إذا المستخدم طلبها.
- استخدم كلمات خليجية بشكل طبيعي مثل:
وش، وشو، وش فيك، وين، ليه، ليش، إيه، أبشر،
تم، حياك، هلا، يا بعدي، ياخي، والله، صدق،
عاد، ترى، الحين، عقب، تو، واجد، زين، كفو،
ما عليك، لا تشيل هم، علومك، وش السالفة.

لا تكثر الكلمات الخليجية بشكل مصطنع.

ممنوع كلمات مثل:
معلش، بص، كده، جامد، إزيك، دلوقتي،
يا معلم، عايز، لسه وغيرها من اللهجة المصرية.

الشخصية:
- ودود.
- عفوي.
- خفيف دم.
- مو رسمي.
- يفهم الطقطقة والمزح.
- إذا المستخدم يمزح امزح معه.
- إذا كان جاد خلك جاد.
- إذا كان متضايق خلك هادي.
- لا تكرر نفس الجمل.
- لا تبدأ كل رد بـ أكيد.
- لا تختم كل رد بسؤال.
- لا تطول إذا السؤال بسيط.
- لا تقول إنك إنسان حقيقي.
- لا تدعي أشياء ما تعرفها.
- لا تخترع ذكريات.

خل ردودك طبيعية كأنها محادثة ديسكورد بين شباب.
"""

# =========================
# الذاكرة
# =========================

db = sqlite3.connect(
    "memory.db",
    check_same_thread=False
)

db.execute("""
CREATE TABLE IF NOT EXISTS memories (
    user_id TEXT,
    memory TEXT
)
""")

db.commit()


def get_memories(user_id):
    rows = db.execute(
        "SELECT memory FROM memories WHERE user_id = ?",
        (user_id,)
    ).fetchall()

    return [x[0] for x in rows]


def save_memory(user_id, memory):
    old = get_memories(user_id)

    if memory.lower() in [x.lower() for x in old]:
        return

    db.execute(
        "INSERT INTO memories (user_id, memory) VALUES (?, ?)",
        (user_id, memory)
    )

    db.commit()


def clear_memory(user_id):
    db.execute(
        "DELETE FROM memories WHERE user_id = ?",
        (user_id,)
    )

    db.commit()


# =========================
# Discord
# =========================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


@bot.event
async def on_ready():
    print("================================")
    print("🔥 لولو اشتغل بنجاح")
    print(f"اسم البوت: {bot.user}")
    print(f"السيرفرات: {len(bot.guilds)}")
    print("================================")


# =========================
# استخراج الذاكرة
# =========================

async def check_memory(user_id, message):

    prompt = f"""
استخرج من رسالة المستخدم أي معلومة شخصية ثابتة ومفيدة
يمكن أن أتذكرها مستقبلًا.

أمثلة:
- اسمه
- لعبة يحبها
- هواية
- فريق يشجعه
- شيء يفضله
- مشروع يعمل عليه

لا تحفظ الكلام العابر أو المزح أو المشاعر المؤقتة.

إذا لم توجد معلومة مهمة اكتب:
NONE

الرسالة:
{message}
"""

    try:
        response = await asyncio.to_thread(
            client.responses.create,
            model=MODEL,
            input=prompt
        )

        result = response.output_text.strip()

        if result and result.upper() != "NONE":
            for line in result.splitlines():
                line = line.strip("-• ").strip()

                if line:
                    save_memory(
                        user_id,
                        line
                    )

    except Exception as e:
        print("Memory error:", e)


# =========================
# الذكاء
# =========================

async def ask_ai(user_id, username, message):

    memories = get_memories(user_id)

    if memories:
        memory_text = "\n".join(
            "- " + x for x in memories[-30:]
        )
    else:
        memory_text = "ما عندي ذكريات محفوظة عن المستخدم."

    prompt = f"""
{SYSTEM}

اسم المستخدم:
{username}

ال
