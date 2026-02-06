from openai import AsyncOpenAI
from pydantic import BaseModel
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

class LLMService:

    def __init__(self, model: str = None):

        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = model or OPENAI_MODEL

    async def invoke(self, prompt: str, max_tokens: int = 100) -> str | None:

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )

        return response.choices[0].message.content

    async def invoke_structured(self, prompt: str, response_model: type[BaseModel], max_tokens: int = 100):
        
        response = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format=response_model,
            max_tokens=max_tokens
        )

        return response.choices[0].message.parsed

_llm = None

def get_llm() -> LLMService:
    
    global _llm
    if _llm is None:
        _llm = LLMService()
    return _llm
