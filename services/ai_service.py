import base64
import logging
import anthropic
from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# Initialize AsyncAnthropic client if key is set
client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "YOUR_ANTHROPIC_API_KEY_HERE" else None

SYSTEM_PROMPT = """Siz "Apteka AI Farmatsevt" deb nomlangan aqlli va professional dorixona yordamchisisiz.
Sizning vazifangiz foydalanuvchilarga dori-darmonlar, ularning ta'sir etuvchi moddalari, qo'llash tartibi va shamollash/bosh og'rig'i/hazm buzilishi kabi simptomlarda yordam berishdir.

Asosiy qoidalar:
1. Har doim samimiy, tushunarli va chiroyli O'zbek tilida javob bering.
2. Dori haqida ma'lumot berayotganda uning asosiy vazifasi, dozasi va nojo'ya ta'sirlari haqida qisqacha tushuntiring.
3. Agarda foydalanuvchi jiddiy kasallik alomatlarini aytsa, zudlik bilan shifokorga murojaat qilishni maslahat bering.
4. Javobingiz oxirida har doim qisqa va aniq tibbiy ogohlantirish (disclaimer) bo'lsin: 
"⚠️ *Eslatma: Ushbu ma'lumot ma'lumot beruvchi xarakterga ega. Aniq tashxis va davolash uchun shifokor bilan maslahatlashish zarur.*"
"""

async def get_pharmacy_consultation(user_query: str) -> str:
    if not client:
        return "⚠️ *Claude API kaliti sozlanmagan.* `.env` faylida `ANTHROPIC_API_KEY` ni ko'rsating."
    
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            temperature=0.3,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_query}
            ]
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude API consultation error: {e}")
        return f"Kechirasiz, AI xizmatida xatolik yuz berdi: {str(e)}"

async def analyze_prescription_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    if not client:
        return "⚠️ *Claude API kaliti sozlanmagan.* `.env` faylida `ANTHROPIC_API_KEY` ni ko'rsating."

    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        prompt_text = """Siz tajribali apteka AI farmatsevtisiz. Ushbu shifokor retsepti yoki dori qutisi tasvirini tahlil qiling.
Undagi:
1. Dori nomlari (Brand yoki generic)
2. Dozasi va qabul qilish tartibi (kunda necha mahal, ovqatdan oldin/so'ng)
3. Ko'rsatilgan izohlar va shifokor tavsiyalarini o'zbek tilida aniq, ravon va tartibli ko'rinishda tushuntirib bering.

Javobingiz oxiriga standard tibbiy ogohlantirish qo'shing:
"⚠️ *Eslatma: Retseptni xariddan oldin shifokor yoki farmatsevt bilan qayta tasdiqlang.*"
"""
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            temperature=0.2,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": base64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt_text
                        }
                    ],
                }
            ],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude Vision API error: {e}")
        return f"Kechirasiz, rasmni tahlil qilishda xatolik yuz berdi: {str(e)}"
