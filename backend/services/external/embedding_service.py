from openai import AsyncOpenAI
from typing import List
from config.settings import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, EMBEDDING_DIM

class EmbeddingService:

    def __init__(self):

        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_EMBEDDING_MODEL

    async def generate_embedding(self, text: str, embedding_dim : int  = EMBEDDING_DIM) -> List[float]:

        response = await self.client.embeddings.create(

            model=self.model,
            input=text,
            dimensions=embedding_dim
        )

        return response.data[0].embedding

    async def generate_embeddings(self, texts: List[str], embedding_dim : int = EMBEDDING_DIM) -> List[List[float]]:

        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions= embedding_dim
        )

        return [item.embedding for item in response.data]

_embedding_service = None

def get_embedding_service() -> EmbeddingService:

    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
