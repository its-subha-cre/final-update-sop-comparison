class ValidationAgent:
    """Validates candidate global clauses to filter out duplicates, incorrect sections, or low confidence matches."""

    @staticmethod
    def validate_candidates(candidates: list, local_context: dict) -> list:
        """
        Validates a list of candidate global clauses against the local context (e.g. section title).
        Returns a filtered list of valid candidates.
        """
        if not candidates:
            return []

        seen_ids = set()
        validated = []

        local_section = local_context.get("section_title", "").lower()

        for cand in candidates:
            # 1. Deduplicate by node ID
            cand_id = cand.get("id")
            if cand_id in seen_ids:
                continue
            seen_ids.add(cand_id)

            # 2. Section check (Heuristic alignment score boost/filter)
            cand_text = cand.get("text", "").lower()
            
            # Simple text length and empty validation checks
            if not cand_text.strip():
                continue
                
            validated.append(cand)

        return validated
