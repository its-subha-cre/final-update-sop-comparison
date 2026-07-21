import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.translation import TranslationAgent, TranslationValidationAgent
from agents.comparison import ComparisonAgent

def test_multilingual_pipeline():
    print("=== STARTING MULTILINGUAL PIPELINE & VALIDATION VERIFICATION ===")

    # 1. Test TranslationValidationAgent
    validator = TranslationValidationAgent(confidence_threshold=0.75)
    orig_text = "1. Propósito\nEste procedimiento define los controles de seguridad obligatorios para la máquina de rayos X en el Sitio 03.\n\n2. Alcance\nEste procedimiento se aplica a todo el personal."
    trans_text = "1. Purpose\nThis procedure defines the mandatory security controls for the X-Ray machine at Site 03.\n\n2. Scope\nThis procedure applies to all personnel."

    validation_result = validator.validate_translation(
        original_text=orig_text,
        translated_text=trans_text,
        detected_lang="es",
        detector_fn=lambda t: "en"
    )

    print(f"Validation Score: {validation_result['confidence_score']:.2f}")
    print(f"Validation Passed: {validation_result['is_valid']}")
    assert validation_result["is_valid"], f"Validation failed unexpectedly: {validation_result['issues']}"
    assert validation_result["confidence_score"] >= 0.75

    # 2. Test Canonical Representation & Original Text Preservation
    agent = TranslationAgent()
    raw_texts = {
        "global": "GLOBAL STANDARD OPERATING PROCEDURE\n1. Purpose\nEnsure security of X-Ray equipment.",
        "local_es": orig_text
    }
    original_raw_texts = {}

    print("Executing TranslationAgent process_raw_texts...")
    metadata = agent.process_raw_texts(raw_texts, original_raw_texts)

    # Check original text preservation
    assert "local_es" in original_raw_texts, "Original raw text was not preserved in original_raw_texts!"
    assert original_raw_texts["local_es"] == orig_text, "Preserved original raw text does not match input!"
    print("Assertion passed: Raw untranslated text retained in original_raw_texts for auditing.")

    # Check canonical English text in raw_texts
    assert "local_es" in raw_texts and len(raw_texts["local_es"]) > 0
    print(f"Canonical state text for local_es (Length: {len(raw_texts['local_es'])}):")
    print(raw_texts["local_es"][:120])

    # 3. Verify ComparisonAgent Similarity Stability
    comparator = ComparisonAgent()
    
    # Global Clause vs Translated Local Clause
    global_clause = "1. Purpose\nThis procedure defines the mandatory security controls for the X-Ray machine at all facilities."
    translated_clause = raw_texts["local_es"].split("\n\n")[0] # "1. Purpose\nThis procedure defines..."
    
    comp_res = comparator.compare_clauses(global_clause, translated_clause)
    print(f"\nComparison result between Global English Clause & Translated Canonical Clause:")
    print(f"  * Lexical Similarity: {comp_res['lexical_similarity']}")
    print(f"  * Semantic Cosine Similarity: {comp_res['semantic_similarity']}")
    print(f"  * Combined Similarity Score: {comp_res['combined_score']:.2f}")

    assert comp_res["combined_score"] >= 0.70, f"Expected high similarity score (>= 0.70), got {comp_res['combined_score']:.2f}"
    print("Assertion passed: Canonical English representation produces consistent high similarity score (~86%).")

    print("\n=== MULTILINGUAL PIPELINE & VALIDATION VERIFICATION PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_multilingual_pipeline()
