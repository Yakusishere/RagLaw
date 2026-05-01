from app.services.query_normalization import normalize_query


def test_normalize_query_strips_outer_whitespace():
    assert normalize_query("  商家拒绝退款怎么办  ") == "商家拒绝退款怎么办"


def test_normalize_query_collapses_internal_whitespace():
    assert normalize_query("商家   拒绝\t退款") == "商家 拒绝 退款"
