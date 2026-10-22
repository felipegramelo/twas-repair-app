import os
import asyncio
import httpx

GEMINI_MODEL = "gemini-3-flash-preview"


async def generate_text(system_message: str, user_text: str, session_id: str = "default") -> str:
    """Use the user's own Gemini key directly (works on external hosts); fall back to Emergent key."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        body = {
            "system_instruction": {"parts": [{"text": system_message}]},
            "contents": [{"parts": [{"text": user_text}]}],
        }
        async with httpx.AsyncClient(timeout=180) as client:
            for attempt in range(4):
                resp = await client.post(url, params={"key": gemini_key}, json=body)
                if resp.status_code in (429, 503) and attempt < 3:
                    await asyncio.sleep(15 * (attempt + 1))
                    continue
                break
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini (chave própria) HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])

    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        raise RuntimeError("GEMINI_API_KEY/EMERGENT_LLM_KEY não configurada no servidor")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=emergent_key, session_id=session_id, system_message=system_message).with_model("gemini", GEMINI_MODEL)
    response = await chat.send_message(UserMessage(text=user_text))
    return response if isinstance(response, str) else str(response)
