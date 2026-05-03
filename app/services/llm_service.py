from collections.abc import Iterator
from pathlib import Path

from openai import OpenAI

from app.schemas.chat import ChatAnswer, ChatResponse, ChatStreamEvent
from app.schemas.retrieval import RetrievalResponse

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "qa_system.txt"
DRAFT_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "drafting_system.txt"


def build_grounded_prompt(retrieval_response: RetrievalResponse) -> str:
    context_blocks = []
    for item in retrieval_response.results:
        context_blocks.append(f"[{item.citation.citation_label}]\n{item.chunk_text}")
    joined_context = "\n\n".join(context_blocks) if context_blocks else "无可用检索依据。"
    return f"用户问题：{retrieval_response.query}\n\n检索依据：\n{joined_context}"


def build_drafting_prompt(
    template_text: str,
    facts: dict[str, str],
    retrieval_response: RetrievalResponse,
) -> str:
    facts_block = "\n".join(f"- {key}: {value}" for key, value in facts.items())
    context_blocks = []
    for item in retrieval_response.results:
        context_blocks.append(f"[{item.citation.citation_label}]\n{item.chunk_text}")
    joined_context = "\n\n".join(context_blocks) if context_blocks else "无可用检索依据。"
    return (
        f"模板正文：\n{template_text}\n\n"
        f"结构化事实：\n{facts_block}\n\n"
        f"检索依据：\n{joined_context}"
    )


def build_insufficient_basis_answer() -> ChatAnswer:
    return ChatAnswer(
        summary="依据不足，当前检索结果未提供足够法条依据。",
        basis=[],
        suggested_steps=["补充交易记录、聊天记录、商品页面截图后再次检索。"],
        risk_notes=["当前回答不应视为确定法律结论。"],
        insufficient_basis=True,
    )


def build_supported_answer_parts(
    retrieval_response: RetrievalResponse,
    summary: str = "",
) -> ChatAnswer:
    return ChatAnswer(
        summary=summary,
        basis=[item.citation.citation_label for item in retrieval_response.results[:3]],
        suggested_steps=["保留证据并先向商家主张退换或赔偿。"],
        risk_notes=["模型回答受限于当前检索材料。"],
        insufficient_basis=False,
    )


def build_stream_citations_payload(
    retrieval_response: RetrievalResponse,
    answer: ChatAnswer,
) -> dict[str, object]:
    return {
        "citations": [item.citation.model_dump(mode="json") for item in retrieval_response.results],
        "retrieval": {"result_count": len(retrieval_response.results)},
        "basis": answer.basis,
        "insufficient_basis": answer.insufficient_basis,
        "suggested_steps": answer.suggested_steps,
        "risk_notes": answer.risk_notes,
    }


class LLMService:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None = None,
        client: OpenAI | None = None,
    ):
        self._client = client or OpenAI(api_key=api_key, base_url=base_url)
        self._model_name = model_name
        self._system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self._drafting_system_prompt = DRAFT_PROMPT_PATH.read_text(encoding="utf-8")

    def answer(self, retrieval_response: RetrievalResponse) -> ChatResponse:
        if not retrieval_response.results:
            return ChatResponse(
                query=retrieval_response.query,
                answer=build_insufficient_basis_answer(),
                citations=[],
                retrieval={"result_count": 0},
            )

        prompt = build_grounded_prompt(retrieval_response)
        try:
            response = self._client.responses.create(
                model=self._model_name,
                input=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:
            raise RuntimeError("上游模型调用失败") from exc
        answer = build_supported_answer_parts(
            retrieval_response,
            summary=response.output_text,
        )

        return ChatResponse(
            query=retrieval_response.query,
            answer=answer,
            citations=[item.citation for item in retrieval_response.results],
            retrieval={"result_count": len(retrieval_response.results)},
        )

    def stream_answer(self, retrieval_response: RetrievalResponse) -> Iterator[ChatStreamEvent]:
        yield ChatStreamEvent(event="meta", data={"query": retrieval_response.query})

        if not retrieval_response.results:
            answer = build_insufficient_basis_answer()
            yield ChatStreamEvent(event="delta", data={"text": answer.summary})
            yield ChatStreamEvent(
                event="citations",
                data=build_stream_citations_payload(retrieval_response, answer),
            )
            yield ChatStreamEvent(event="done", data={"ok": True})
            return

        prompt = build_grounded_prompt(retrieval_response)
        answer = build_supported_answer_parts(retrieval_response)

        try:
            with self._client.responses.stream(
                model=self._model_name,
                input=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": prompt},
                ],
            ) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta" and event.delta:
                        yield ChatStreamEvent(event="delta", data={"text": event.delta})
        except Exception as exc:
            yield ChatStreamEvent(event="error", data={"message": str(exc) or "上游模型调用失败"})
            return

        yield ChatStreamEvent(
            event="citations",
            data=build_stream_citations_payload(retrieval_response, answer),
        )
        yield ChatStreamEvent(event="done", data={"ok": True})

    def draft_document(
        self,
        *,
        template_text: str,
        facts: dict[str, str],
        retrieval_response: RetrievalResponse,
    ) -> str:
        prompt = build_drafting_prompt(template_text, facts, retrieval_response)
        try:
            response = self._client.responses.create(
                model=self._model_name,
                input=[
                    {"role": "system", "content": self._drafting_system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:
            raise RuntimeError("上游模型调用失败") from exc
        return response.output_text.strip()
