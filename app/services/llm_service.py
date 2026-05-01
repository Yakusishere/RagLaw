from pathlib import Path

from openai import OpenAI

from app.schemas.chat import ChatAnswer, ChatResponse
from app.schemas.retrieval import RetrievalResponse


def build_grounded_prompt(retrieval_response: RetrievalResponse) -> str:
    context_blocks = []
    for item in retrieval_response.results:
        context_blocks.append(f"[{item.citation.citation_label}]\n{item.chunk_text}")
    joined_context = "\n\n".join(context_blocks) if context_blocks else "无可用检索依据。"
    return f"用户问题：{retrieval_response.query}\n\n检索依据：\n{joined_context}"


class LLMService:
    def __init__(self, api_key: str, model_name: str):
        self._client = OpenAI(api_key=api_key)
        self._model_name = model_name
        self._system_prompt = Path("app/prompts/qa_system.txt").read_text(encoding="utf-8")

    def answer(self, retrieval_response: RetrievalResponse) -> ChatResponse:
        if not retrieval_response.results:
            return ChatResponse(
                query=retrieval_response.query,
                answer=ChatAnswer(
                    summary="依据不足，当前检索结果未提供足够法条依据。",
                    basis=[],
                    suggested_steps=["补充交易记录、聊天记录、商品页面截图后再次检索。"],
                    risk_notes=["当前回答不应视为确定法律结论。"],
                    insufficient_basis=True,
                ),
                citations=[],
                retrieval={"result_count": 0},
            )

        prompt = build_grounded_prompt(retrieval_response)
        response = self._client.responses.create(
            model=self._model_name,
            input=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        text = response.output_text

        return ChatResponse(
            query=retrieval_response.query,
            answer=ChatAnswer(
                summary=text,
                basis=[item.citation.citation_label for item in retrieval_response.results[:3]],
                suggested_steps=["保留证据并先向商家主张退换或赔偿。"],
                risk_notes=["模型回答受限于当前检索材料。"],
                insufficient_basis=False,
            ),
            citations=[item.citation for item in retrieval_response.results],
            retrieval={"result_count": len(retrieval_response.results)},
        )
