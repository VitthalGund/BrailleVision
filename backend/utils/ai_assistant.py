import os
import logging
import httpx
import anthropic

logger = logging.getLogger(__name__)

MOCK_RESPONSES = {
    "hello": "Hello! I am your Dotly Assistant. How can I help you read or understand Braille today?",
    "help": "To scan Braille with Dotly, ensure your camera has good side lighting (raking light) to cast clear shadows on the dots. Keep the paper flat.",
    "lighting": "Side lighting (raking light) is best for embossed Braille because it casts clear shadows on the raised bumps, making them visible to the camera.",
    "distance": "Hold the camera about 6 to 10 inches away from the Braille page, keeping it flat and level for the best recognition accuracy.",
    "grade 1": "Grade 1 Braille is a letter-for-letter translation of print text. Every print character is mapped directly to one Braille cell.",
    "grade 2": "Grade 2 Braille uses contractions and abbreviations to save space. For example, the word 'the' is represented by a single cell. Currently, Dotly supports Grade 1.",
    "w": "In English Braille, the letter 'w' is represented by dots 2,4,5,6 (⠺). It was added later to the Braille alphabet because French didn't use 'w' originally!",
    "capital": "In Grade 1 Braille, a capital letter is indicated by preceding the letter with a capital indicator cell (dot 6: ⠠).",
    "number": "Numbers are written using the letters 'a' through 'j' preceded by the number indicator cell (dots 3,4,5,6: ⠼). For example, '#a' means '1'.",
    "alignment": "For best alignment, hold your camera perfectly parallel to the Braille surface (not tilted). Keep the camera steady and maintain a distance of 6-10 inches.",
    "tips": "Tips for high accuracy: 1. Use strong raking light (light from the side). 2. Keep the camera flat and steady. 3. Avoid wrinkles. 4. Center the text in the camera view.",
    "camera": "Hold the camera steady, parallel to the page, and at a distance of 6-10 inches. Good lighting from the side is key to resolving the raised dots.",
    "thanks": "You're welcome! Let me know if you need help with anything else.",
    "thank you": "You're welcome! Let me know if you need help with anything else.",
    "braille": "Braille is a tactile system of writing for visually impaired people, using cells of raised dots (up to 6 dots in a 2x3 grid) to represent letters, numbers, and symbols.",
}

class AIAssistant:
    @staticmethod
    async def get_reply(message: str, context: str = "", history: list = None) -> str:
        """
        Get chat response from the configured AI provider.
        Supported providers: 'mock' (default), 'openai', 'ollama', 'anthropic'.
        """
        provider = os.getenv("AI_PROVIDER", "mock").lower()
        
        # If keys are present, automatically upgrade provider from mock
        if provider == "mock":
            if os.getenv("ANTHROPIC_API_KEY"):
                provider = "anthropic"
            elif os.getenv("OPENAI_API_KEY"):
                provider = "openai"
            elif os.getenv("OLLAMA_URL"):
                provider = "ollama"

        logger.info(f"AI Assistant using provider: {provider}")

        if provider == "anthropic":
            return await AIAssistant._call_anthropic(message, context, history)
        elif provider == "openai":
            return await AIAssistant._call_openai(message, context, history)
        elif provider == "ollama":
            return await AIAssistant._call_ollama(message, context, history)
        else:
            return AIAssistant._get_mock_reply(message, context)

    @staticmethod
    def _get_mock_reply(message: str, context: str) -> str:
        """Simple rule-based mock responses for offline/keyless development."""
        msg_lower = message.lower()
        
        # Check keyword matches
        for key, resp in MOCK_RESPONSES.items():
            if key in msg_lower:
                return resp
                
        # Handle context in mock
        if context and "scan" in msg_lower or "read" in msg_lower:
            return f"I see your recent scan recognized: '{context}'. If some characters look wrong, check the lighting and try keeping the camera steadier."

        return (
            "I am your Dotly offline assistant. You can ask me about: "
            "lighting, scan distance, Grade 1 vs Grade 2 Braille, or special symbols like capitals and numbers!"
        )

    @staticmethod
    async def _call_anthropic(message: str, context: str, history: list) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return "Anthropic API key missing. Please set ANTHROPIC_API_KEY."

        system_prompt = f"""You are BrailleVision Assistant — a helpful, concise AI assistant built into a Braille reading app.
Your role:
- Help users understand Braille symbols and the Braille system
- Guide users on how to best scan physical Braille with their camera (lighting, angle, distance)
- Provide context for text that has been recognized from Braille
- Answer accessibility-related questions
Keep responses concise (2-4 sentences) and practical.
Current app context: {context or 'No recent scan'}"""

        try:
            client = anthropic.Anthropic(api_key=api_key)
            messages = []
            if history:
                for turn in history[-6:]:
                    if turn.get("role") in ("user", "assistant") and turn.get("content"):
                        messages.append({"role": turn["role"], "content": turn["content"]})
            messages.append({"role": "user", "content": message})

            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=300,
                system=system_prompt,
                messages=messages,
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            return "I'm having trouble connecting to Anthropic. Using mock mode: " + AIAssistant._get_mock_reply(message, context)

    @staticmethod
    async def _call_openai(message: str, context: str, history: list) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        if not api_key:
            return "OpenAI API key missing. Please set OPENAI_API_KEY."

        system_msg = {
            "role": "system",
            "content": f"You are BrailleVision Assistant. Help users read and understand Braille. Keep responses to 2-3 sentences. Context: {context or 'No recent scan'}"
        }

        try:
            messages = [system_msg]
            if history:
                for turn in history[-6:]:
                    if turn.get("role") in ("user", "assistant") and turn.get("content"):
                        messages.append({"role": turn["role"], "content": turn["content"]})
            messages.append({"role": "user", "content": message})

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": model, "messages": messages, "max_tokens": 150}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    return f"OpenAI API returned error: {resp.text}"
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
            return "Failed to connect to OpenAI service."

    @staticmethod
    async def _call_ollama(message: str, context: str, history: list) -> str:
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
        model = os.getenv("OLLAMA_MODEL", "llama3")

        system_prompt = f"You are BrailleVision Assistant. Help users with Braille accessibility. Keep replies short. Context: {context}"
        
        try:
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                for turn in history[-6:]:
                    if turn.get("role") in ("user", "assistant") and turn.get("content"):
                        messages.append({"role": turn["role"], "content": turn["content"]})
            messages.append({"role": "user", "content": message})

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    ollama_url,
                    json={"model": model, "messages": messages, "stream": False}
                )
                if resp.status_code == 200:
                    return resp.json()["message"]["content"].strip()
                else:
                    return f"Ollama returned error status: {resp.status_code}"
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return "Could not reach local Ollama AI model server."
