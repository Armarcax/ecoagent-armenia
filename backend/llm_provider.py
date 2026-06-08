"""
EcoAgent Armenia — LLM Provider
Priority: Google Gemini (free) → Groq (free) → No-LLM (context only)
"""

import os
import json
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

LLM_PRIORITY = os.getenv("LLM_PROVIDER_PRIORITY", "google,groq,none").split(",")
MAX_TOKENS   = int(os.getenv("MAX_TOKENS", "1000"))

SYSTEM_PROMPT = """Դու EcoAgent Armenia-ն ես — Հայաuтанի բnap ahpanakan-tntesagitakan AI khordrdatun:

ԿАРGАVОR КАНОН — Пататaskhan МIAYN МАQUR HAYEREN LEZVIOV haykaкan tarrerrov (Ա Բ Գ Դ...).
Latin tarrerr ev transliteraciya ARGELVUM EN КАТЕГОРИKОRPEN.

КАNONNER:
1. Pataskhanir МIAYN tramadrvats context-i himan vra
2. Ete context-um teghekvatyun chka — asa "Ays harcin veraberyal HH konkret tval chunem"
3. МISHT nshir hghumnner — orenkky anvanumen, hodvatsы, URL
4. Pataskhhany karrucir hstakketovov hayeren
5. Ogtagortsir hayeren — profesional, bayts haskanali

KARRUCVACQ:
✅ Orch e pahanjum orenky
📋 Anhhrazhesht phastatgher / tuylattvutyunner
⚠️ Riskser / Tugankner
🔗 Aghbyurner"""


async def _try_google(user_message: str) -> AsyncGenerator[str, None]:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    model   = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash-exp")
    if not api_key:
        raise ValueError("No GOOGLE_API_KEY")
    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
    body = {
        "contents": [
            {"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{user_message}"}]}
        ],
        "generationConfig": {"maxOutputTokens": MAX_TOKENS, "temperature": 0.3},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, json=body) as resp:
            if resp.status_code != 200:
                text = await resp.aread()
                raise ValueError(f"Google API {resp.status_code}: {text[:200]}")
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    try:
                        data = json.loads(line[5:].strip())
                        chunk = (
                            data.get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", "")
                        )
                        if chunk:
                            yield chunk
                    except Exception:
                        pass


async def _try_groq(user_message: str) -> AsyncGenerator[str, None]:
    api_key = os.getenv("GROQ_API_KEY", "")
    model   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if not api_key:
        raise ValueError("No GROQ_API_KEY")
    import httpx
    url  = "https://api.groq.com/openai/v1/chat/completions"
    body = {
        "model":       model,
        "max_tokens":  MAX_TOKENS,
        "temperature": 0.3,
        "stream":      True,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, json=body,
                                 headers={"Authorization": f"Bearer {api_key}"}) as resp:
            if resp.status_code != 200:
                text = await resp.aread()
                raise ValueError(f"Groq API {resp.status_code}: {text[:200]}")
            async for line in resp.aiter_lines():
                if line.startswith("data:") and "[DONE]" not in line:
                    try:
                        data  = json.loads(line[5:].strip())
                        chunk = data["choices"][0]["delta"].get("content", "")
                        if chunk:
                            yield chunk
                    except Exception:
                        pass


async def _no_llm(user_message: str) -> AsyncGenerator[str, None]:
    """Fallback — returns context directly without LLM."""
    import re
    match = re.search(r"CONTEXT:\n(.*?)\n\nPataskhanir", user_message, re.DOTALL)
    if not match:
        match = re.search(r"НARЦ:.*?\n\n(.*)", user_message, re.DOTALL)
    context = match.group(1).strip() if match else "Теghekvatyun chi gtnvel."
    yield f"📄 **Ваш запрос найден в следующих документах:**\n\n{context[:2000]}\n\n_Ответ основан на внутренней базе документов._"


async def generate_response(
    system_prompt: str,
    user_message: str,
    stream: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Try providers in priority order.
    LLM_PROVIDER_PRIORITY=google,groq,none
    """
    last_error = None
    for provider in LLM_PRIORITY:
        provider = provider.strip().lower()
        try:
            if provider == "google":
                async for chunk in _try_google(user_message):
                    yield chunk
                return
            elif provider == "groq":
                async for chunk in _try_groq(user_message):
                    yield chunk
                return
            elif provider in ("none", "local"):
                async for chunk in _no_llm(user_message):
                    yield chunk
                return
        except Exception as e:
            print(f"[⚠️] Provider '{provider}' failed: {e}")
            last_error = e
            continue

    # All failed
    yield f"⚠️ Բոло провайдеры сkhалел en: {last_error}"
