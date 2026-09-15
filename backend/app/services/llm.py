from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings

settings = get_settings()


@lru_cache
def get_llm() -> ChatGoogleGenerativeAI:
    """Create the cloud LLM client once per API process."""
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Create a free Gemini API key in Google AI Studio "
            "and add it to .env."
        )

    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        api_key=settings.gemini_api_key,
        temperature=0,
        thinking_budget=settings.llm_thinking_budget,
        max_retries=2,
    )


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


def grounded_answer(question: str, context: str, history: list[dict[str, str]]) -> str:
    llm = get_llm()
    history_text = "\n".join(f"{item['role']}: {item['content']}" for item in history[-6:])
    prompt = f"""
You are a document-grounded AI assistant.

Rules:
1. Answer using only the supplied source context.
2. If the context does not contain enough evidence, say that you could not find enough information in the uploaded documents.
3. Do not invent citations, facts, page numbers, or source names.
4. Cite factual claims using [SOURCE N] markers from the supplied context.
5. Prefer a concise, technically precise answer.

Conversation history:
{history_text or '(none)'}

Question:
{question}

Source context:
{context or '(no relevant context found)'}
"""
    response = llm.invoke(prompt)
    return _content_to_text(response.content)
