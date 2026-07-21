import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.translation import TranslationAgent

def test_translation_agent_suite():
    print("=== STARTING ENTERPRISE TRANSLATION AGENT VERIFICATION ===")

    agent = TranslationAgent(chunk_size=1000, max_workers=2)

    # 1. Test Language Detection (English)
    english_sample = "1. Purpose\nThis procedure defines the mandatory security controls for X-Ray equipment."
    lang_en = agent.detect_language(english_sample)
    print(f"English text detected language: '{lang_en}'")
    assert lang_en in ["en", "english"], f"Expected English detection, got '{lang_en}'"

    # 2. Test Language Detection (Spanish sample)
    spanish_sample = "1. Propósito\nEste procedimiento define los controles de seguridad obligatorios para el uso seguro del equipo de rayos X."
    lang_es = agent.detect_language(spanish_sample)
    print(f"Spanish text detected language: '{lang_es}'")
    assert lang_es not in ["en", "english"], f"Expected non-English detection, got '{lang_es}'"

    # 3. Test Incremental Chunking
    multi_paragraph_text = "\n\n".join([f"Paragraph {i}: " + ("Content details. " * 50) for i in range(5)])
    chunks = agent._chunk_text(multi_paragraph_text)
    print(f"Multi-paragraph text split into {len(chunks)} chunks successfully.")
    assert len(chunks) > 1, "Expected multiple chunks for large text!"

    # 4. Test In-place State Processing & Fallback Resilience
    raw_texts = {
        "global": "GLOBAL STANDARD OPERATING PROCEDURE\n1. Purpose\nEnsure security of equipment.",
        "local_es": "PROCEDIMIENTO DE OPERACIÓN LOCAL\n1. Propósito\nEste procedimiento define las normas locales para la máquina de rayos X en el Sitio 03."
    }

    print("Executing process_raw_texts on sample SOP dictionary...")
    processed_texts = agent.process_raw_texts(raw_texts)

    print("\n--- PROCESSED RESULT FOR GLOBAL ---")
    print(processed_texts["global"][:150])

    print("\n--- PROCESSED RESULT FOR LOCAL SPANISH ---")
    print(processed_texts["local_es"][:150])

    assert "global" in processed_texts and len(processed_texts["global"]) > 0
    assert "local_es" in processed_texts and len(processed_texts["local_es"]) > 0
    print("Assertion passed: process_raw_texts executes resiliently without crashing pipeline.")

    print("\n=== ENTERPRISE TRANSLATION AGENT VERIFICATION PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_translation_agent_suite()
