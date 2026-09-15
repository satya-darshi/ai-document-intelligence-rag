from uuid import UUID

from langchain.agents import create_agent
from langchain.tools import tool
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.llm import get_llm
from app.services.retrieval import build_context, retrieve

settings = get_settings()


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


class AgentRunner:
    def __init__(self, db: Session, document_ids: list[UUID]):
        self.db = db
        self.document_ids = document_ids
        self.last_chunks = []

    def run(self, question: str, history: list[dict[str, str]]) -> tuple[str, list]:
        runner = self

        @tool
        def search_documents(query: str) -> str:
            """Search the uploaded documents for evidence relevant to a question."""
            chunks = retrieve(query, runner.document_ids, runner.db, limit=settings.rerank_top_k)
            runner.last_chunks = chunks
            return build_context(chunks)

        @tool
        def inspect_source(source_index: int) -> str:
            """Return the full text of a retrieved source by 1-based source index."""
            chunks = runner.last_chunks
            if source_index < 1 or source_index > len(chunks):
                return "Invalid source index. Search the documents first."
            chunk = chunks[source_index - 1]
            page = f"page {chunk.page}" if chunk.page else "unknown page"
            return f"[SOURCE {source_index}] {chunk.filename}, {page}:\n{chunk.text}"

        @tool
        def compare_documents(topic: str) -> str:
            """Retrieve evidence about a topic across all selected documents for comparison."""
            chunks = retrieve(topic, runner.document_ids, runner.db, limit=settings.rerank_top_k)
            runner.last_chunks = chunks
            return build_context(chunks)

        prompt = """
You are an AI document analyst with access to uploaded documents through tools.

Rules:
- Use a document-search tool before making factual claims about the uploaded documents.
- Use compare_documents when the user asks to compare documents or approaches.
- Use inspect_source when you need to verify the exact text of a retrieved source.
- Never invent facts, citations, page numbers, or source names.
- If the retrieved evidence is insufficient, explicitly say so.
- Preserve [SOURCE N] markers from tool results when citing evidence.
- Give concise, technically precise answers.
"""
        agent = create_agent(
            model=get_llm(),
            tools=[search_documents, inspect_source, compare_documents],
            system_prompt=prompt,
        )
        history_messages = [
            {"role": item["role"], "content": item["content"]} for item in history[-6:]
        ]
        result = agent.invoke({"messages": history_messages + [{"role": "user", "content": question}]})
        answer = _content_to_text(result["messages"][-1].content)
        return answer, runner.last_chunks
