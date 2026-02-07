from pinecone import Pinecone
from typing import List, Any, Optional
from config.settings import PINECONE_API_KEY, PINECONE_INDEX_NAME, PINECONE_NAMESPACE

VectorTupleWithMetadata = tuple[str, list[float], dict[str, Any]]
class PineconeService:

    def __init__(self):

        self.client = Pinecone(api_key=PINECONE_API_KEY)
        self.index = self.client.Index(PINECONE_INDEX_NAME)

    async def upsert(self, vectors: list[VectorTupleWithMetadata], namespace : str = PINECONE_NAMESPACE):

        self.index.upsert(vectors= vectors, namespace= namespace)

    async def query(self, vector: List[float], top_k: int = 5, filter: Optional[dict[str, Any]] = None, namespace: str = PINECONE_NAMESPACE):

        return self.index.query(
            vector=vector,
            top_k=top_k,
            filter=filter or {},
            include_metadata=True,
            namespace=namespace
        )

    async def delete(self, ids: List[str]):

        self.index.delete(ids=ids)

_pinecone_service = None

def get_pinecone_service() -> PineconeService:

    global _pinecone_service
    if _pinecone_service is None:
        _pinecone_service = PineconeService()

    return _pinecone_service
