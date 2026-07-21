import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set console output encoding to utf-8 for Windows compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agents.translation import TranslationAgent
from agents.llm_chunker import LLMChunkerAgent

def test_chinese_sop_translation_flow():
    print("=== STARTING CHINESE SOP TRANSLATION & CANONICAL CHUNKING TEST ===")

    agent = TranslationAgent()

    chinese_sop_text = """
GLOBAL STANDARD OPERATING PROCEDURE

1. 目的
本程序定义了 across all facilities 的 X-Ray 设备的强制性安全控制。

2. 范围
本程序适用于所有 X-Ray 设备和关联区域。

3. 职责
安全官负责批准人员进入 X-Ray 房间。

4. 访问控制
只有经培训并获得授权的人员才能操作 X-Ray 机器。

5. 安全控制
在不使用 X-Ray 机器时，房间必须始终上锁。
"""

    raw_texts = {
        "global": "GLOBAL STANDARD OPERATING PROCEDURE\n1. Purpose\nThis procedure defines mandatory safety controls for X-Ray equipment.",
        "chinese_local": chinese_sop_text
    }
    original_raw_texts = {}

    print("Step 1: Running TranslationAgent on Chinese SOP...")
    metadata = agent.process_raw_texts(raw_texts, original_raw_texts)

    print("\n--- TRANSLATION METADATA ---")
    print(metadata)

    translated_english = raw_texts["chinese_local"]
    print("\n--- TRANSLATED CANONICAL ENGLISH TEXT ---")
    print(repr(translated_english[:300]))

    # Assertions
    assert "chinese_local" in original_raw_texts, "Original raw text was not preserved!"
    assert original_raw_texts["chinese_local"] == chinese_sop_text, "Original text preserved is inaccurate!"
    
    # Verify translated text contains English section titles
    translated_lower = translated_english.lower()
    assert "scope" in translated_lower or "purpose" in translated_lower or "responsibilities" in translated_lower, "Translated text does not contain English section headers!"

    print("\nStep 2: Testing downstream LLM Chunking on Canonical English text...")
    chunker = LLMChunkerAgent()
    chunk_res = chunker.chunk_document_with_llm(
        doc_title="LSOP-XRAY-SITE04_Chinese.docx",
        raw_text=translated_english
    )

    print(f"Total chunks created from translated text: {len(chunk_res.chunks)}")
    for c in chunk_res.chunks:
        print(f"  * Chunk ID: {c.id} | Label: {c.label} | Content: {repr(c.content[:60])}")

    assert len(chunk_res.chunks) >= 3, "Expected at least 3 chunks from translated text!"
    print("\n=== CHINESE SOP TRANSLATION & CANONICAL CHUNKING TEST PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_chinese_sop_translation_flow()
