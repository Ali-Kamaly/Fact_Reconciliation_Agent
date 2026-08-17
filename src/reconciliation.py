from config import (
    MAX_ACCEPTABLE_DISAGREEMENT,
    HIGH_DISAGREEMENT,
    MAX_RECENT_AGE
)

def calculate_confidence(evaluation):
    successful_count = evaluation["successful_source_count"]
    unique_provenances = evaluation["unique_known_provenance_count"]
    max_difference = evaluation["max_pairwise_difference"]

    recent_source_count = sum(source['age']<= MAX_RECENT_AGE
                            for source in evaluation["source_ages"])

    if (
        successful_count <2 
        or unique_provenances <2
        or recent_source_count == 0
        or max_difference>HIGH_DISAGREEMENT
    ):
        return "low"

    if (
        successful_count <3
        or unique_provenances <3
        or max_difference>MAX_ACCEPTABLE_DISAGREEMENT
        or recent_source_count <2
    ):
        return "medium"

    return "high"