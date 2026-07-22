import os
import tempfile

os.environ["APP_DATA_DIR"] = tempfile.mkdtemp(prefix="plant-knowledge-test-")

from app.main import KnowledgeInput, chunks_for, infer_equipment_tag, local_answer, local_card


def test_chunking_keeps_all_words_in_order():
    text = " ".join(f"word{number}" for number in range(1003))
    chunks = chunks_for(text, words_per_chunk=500)
    assert [len(chunk.split()) for chunk in chunks] == [500, 500, 3]
    assert chunks[0].startswith("word0")
    assert chunks[-1].endswith("word1002")


def test_equipment_tag_prefers_specific_asset_tag():
    assert infer_equipment_tag("P-101 suction pressure is unstable") == "P-101"
    assert infer_equipment_tag("aeration blower filter procedure") == "aeration blower"
    assert infer_equipment_tag("a general site note") == "general"


def test_local_card_preserves_captured_knowledge_without_inventing_detail():
    values = KnowledgeInput(
        expert_name="Maya Patel",
        role_experience="Technician, 18 years",
        equipment="Pump P-101",
        common_problem="Low flow",
        first_check="Check strainer pressure",
        root_cause="Blocked strainer",
        fix_workaround="Clean the strainer",
        junior_mistake="Increase speed first",
        warning_sign="",
    )
    card = local_card(values)
    assert "Equipment: Pump P-101" in card
    assert "Warning Signs: Not specified" in card
    assert "Contributed by: Maya Patel" in card


def test_local_answer_labels_document_and_expert_evidence():
    answer = local_answer("What should I check?", [
        {"text": "Check suction pressure.", "source": {"citation": "S1", "doc_type": "document"}},
        {"text": "Clean the strainer.", "source": {"citation": "S2", "doc_type": "expert_knowledge"}},
    ])
    assert "Document excerpt [S1]" in answer
    assert "Expert knowledge [S2]" in answer
