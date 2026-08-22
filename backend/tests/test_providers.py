from app.providers.mock import MockProvider
from app.schemas import ProviderResult


def test_mock_provider_result_is_valid_and_bounded(tmp_path):
    import asyncio

    result = asyncio.run(MockProvider().analyze(tmp_path / "input.mp4", 180_000))
    assert isinstance(result, ProviderResult)
    assert len(result.segments) == 3
    assert all(segment.end_ms <= 180_000 for segment in result.segments)
