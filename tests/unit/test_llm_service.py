from app.schemas.retrieval import CitationPayload, RetrievalResponse, RetrievalResultItem
from app.services.llm_service import build_grounded_prompt


def test_build_grounded_prompt_includes_citation_labels():
    response = RetrievalResponse(
        query="商家拒绝退款怎么办",
        results=[
            RetrievalResultItem(
                chunk_id="law:1",
                doc_type="law",
                title="中华人民共和国消费者权益保护法",
                article_no="第二十四条",
                chunk_text="第二十四条 经营者提供的商品或者服务不符合质量要求的...",
                citation=CitationPayload(
                    chunk_id="law:1",
                    citation_label="《中华人民共和国消费者权益保护法》第二十四条",
                    title="中华人民共和国消费者权益保护法",
                    doc_type="law",
                    article_no="第二十四条",
                    effective_date="2013-10-25",
                    source_name="用户提供资料",
                    source_url="",
                ),
                scores={"vector_score": 0.9, "keyword_score": 0.7, "hybrid_score": 0.84},
            )
        ],
    )

    prompt = build_grounded_prompt(response)

    assert "《中华人民共和国消费者权益保护法》第二十四条" in prompt
