import re
import uuid

class ChunkerService:
    """Deterministic, non-LLM Chunking Service.
    Splits raw text structures into Section -> Clause hierarchies.
    """

    @staticmethod
    def chunk_document(sop_id: str, raw_text: str) -> dict:
        """
        Parses text and extracts a nested dictionary representing sections and clauses.
        Treats every single line as a comparable clause so no text is ever skipped.
        """
        lines = raw_text.split('\n')
        
        sop_data = {
            "sop_id": sop_id,
            "sections": []
        }

        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 1. Identify Section: e.g. "1. Purpose", "Section 1", or metadata categories
            if re.match(r'^(\d+(\.\d+)?\.?\s+[a-zA-Z\s]{3,}|Section\s+\d+|[A-Z\s\-_]{4,}:)', line, re.IGNORECASE):
                section_id = f"sec-{uuid.uuid4().hex[:8]}"
                current_section = {
                    "id": section_id,
                    "title": line,
                    "clauses": []
                }
                sop_data["sections"].append(current_section)
                
            # 2. Treat every other line as a comparable clause under the active section
            else:
                if not current_section:
                    # Create a default metadata section at the beginning of the file
                    section_id = f"sec-{uuid.uuid4().hex[:8]}"
                    current_section = {
                        "id": section_id,
                        "title": "Document Metadata & Header",
                        "clauses": []
                    }
                    sop_data["sections"].append(current_section)
                
                clause_id = f"cls-{uuid.uuid4().hex[:8]}"
                # Extract simple numbering or index if present, else label as general
                num_match = re.match(r'^([a-zA-Z0-9]\.|\d+(\.\d+)+|●|\-)\s*', line)
                clause_num = num_match.group(0).strip() if num_match else "Info"
                
                current_section["clauses"].append({
                    "id": clause_id,
                    "number": clause_num,
                    "text": line,
                    "requirements": []
                })

        return sop_data
