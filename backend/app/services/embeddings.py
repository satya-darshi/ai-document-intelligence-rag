from functools import lru_cache

from google import genai
from google.genai import types
from langchain_core.embeddings import Embeddings

from app.core.config import get_settings

settings = get_settings()


class GeminiEmbeddings(Embeddings):
    """LangChain-compatible wrapper around Gemini Embedding 2.

    Gemini Embedding 2 uses different text prefixes for retrieval queries and
    indexed documents. The prefixes are part of Google's recommended retrieval
    format and keep query/document embeddings aligned for asymmetric search.
    """

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured. Create a free Gemini API key in Google AI Studio."
            )
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.batch_size = settings.embedding_batch_size

    def _embed(self, contents: list[types.Content]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for start in range(0, len(contents), self.batch_size):
            batch = contents[start : start + self.batch_size]
            response = self.client.models.embed_content(
                model=self.model,
                contents=batch,
                config=types.EmbedContentConfig(output_dimensionality=self.dimension),
            )
            batch_embeddings = [list(item.values) for item in response.embeddings]
            if len(batch_embeddings) != len(batch):
                raise RuntimeError(
                    f"Gemini returned {len(batch_embeddings)} embeddings for {len(batch)} inputs."
                )
            embeddings.extend(batch_embeddings)
        return embeddings

    @staticmethod
    def _document_content(text: str) -> types.Content:
        formatted = f"title: none | text: {text}"
        return types.Content(parts=[types.Part.from_text(text=formatted)])

    @staticmethod
    def _query_content(text: str) -> types.Content:
        formatted = f"task: search result | query: {text}"
        return types.Content(parts=[types.Part.from_text(text=formatted)])

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed([self._document_content(text) for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._embed([self._query_content(text)])[0]


@lru_cache
def get_embeddings() -> GeminiEmbeddings:
    return GeminiEmbeddings()
