from typing import Union
from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
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
_langchain_llm = None

def get_llm(use_langchain: bool = False) -> Union[ChatOpenAI, LLMService]:

    global _llm, _langchain_llm

    if use_langchain:

        if _langchain_llm is None:
            _langchain_llm = ChatOpenAI(
                model=OPENAI_MODEL,
                temperature=0
            )

        return _langchain_llm

    else:

        if _llm is None:
            _llm = LLMService()
        return _llm
