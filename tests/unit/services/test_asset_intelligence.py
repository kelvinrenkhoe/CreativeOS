import pytest

from services.asset_intelligence import AssetIntelligenceService
from services.campaign_memory import CampaignMemory


def _memory(*contents: str) -> CampaignMemory:
    memory = CampaignMemory()
    for index, content in enumerate(contents):
        memory.add(
            relative_path=f"assets/{index}.md",
            purpose=f"Asset {index}",
            content=content,
        )
    return memory


def test_empty_memory_marks_content_as_novel() -> None:
    assessment = AssetIntelligenceService().assess("A completely new idea", CampaignMemory())

    assert assessment.novelty_score == 1
    assert assessment.similarity_score == 0
    assert not assessment.is_repetitive
    assert assessment.closest_entry is None
    assert assessment.recommendation == "use"


def test_identical_content_is_repetitive() -> None:
    memory = _memory("Follow the journey and stream the new single today")

    assessment = AssetIntelligenceService().assess(
        "Follow the journey and stream the new single today",
        memory,
    )

    assert assessment.novelty_score == 0
    assert assessment.similarity_score == 1
    assert assessment.is_repetitive
    assert assessment.closest_entry == memory.entries[0]
    assert assessment.recommendation == "revise"


def test_assessment_identifies_closest_prior_asset() -> None:
    memory = _memory(
        "A quiet portrait introduces the artist",
        "Follow the journey through the city at night",
    )

    assessment = AssetIntelligenceService(repetition_threshold=0.9).assess(
        "Follow the journey through the city at sunrise",
        memory,
    )

    assert assessment.closest_entry == memory.entries[1]
    assert assessment.similarity_score > 0
    assert not assessment.is_repetitive


def test_comparison_is_case_and_punctuation_insensitive() -> None:
    memory = _memory("PRESS PLAY, and share the story!")

    assessment = AssetIntelligenceService().assess(
        "Press play and share the story",
        memory,
    )

    assert assessment.similarity_score == 1
    assert assessment.is_repetitive


@pytest.mark.parametrize(
    ("threshold", "message"),
    [
        (-0.1, "repetition_threshold"),
        (1.1, "repetition_threshold"),
    ],
)
def test_rejects_invalid_threshold(threshold: float, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        AssetIntelligenceService(repetition_threshold=threshold)


def test_rejects_invalid_shingle_size() -> None:
    with pytest.raises(ValueError, match="shingle_size"):
        AssetIntelligenceService(shingle_size=0)


def test_rejects_empty_content() -> None:
    with pytest.raises(ValueError, match="content"):
        AssetIntelligenceService().assess("   ", CampaignMemory())
