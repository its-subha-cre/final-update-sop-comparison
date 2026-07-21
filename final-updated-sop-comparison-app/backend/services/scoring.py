class ScoringService:
    """Computes similarity and local SOP necessity scores deterministically."""

    @staticmethod
    def calculate_similarity_score(lexical_sim: float, embedding_sim: float, 
                                    w_lexical: float = 0.3, w_embedding: float = 0.7) -> float:
        """
        Calculates similarity using a weighted average of embedding and lexical similarities.
        """
        score = (w_lexical * lexical_sim) + (w_embedding * embedding_sim)
        return round(min(max(score, 0.0), 1.0), 3)

    @staticmethod
    def calculate_necessity_score(total_deviations: int, justified_deviations: int) -> float:
        """
        Computes the Local SOP Necessity Score:
        Measures if local modifications are justified by regulatory/site context,
        or are simply arbitrary deviations.
        """
        if total_deviations == 0:
            return 1.0  # Perfect alignment / no unnecessary deviations
        
        necessity = justified_deviations / total_deviations
        return round(min(max(necessity, 0.0), 1.0), 3)
