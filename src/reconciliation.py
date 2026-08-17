from config import (
    MAX_ACCEPTABLE_DISAGREEMENT,
    HIGH_DISAGREEMENT,
    MAX_RECENT_AGE
)
from evaluation import get_successful_evidence

QUALITY_RANK = {
    "high": 2,
    "medium": 1,
    "unknown": 0
}

#intentionally not using precise probability
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

def choose_best_evidence(evidence_list, evaluation):
    #successful evidence only
    #- highest source quality wins
    #- if quality ties, freshest year wins

    successful_evidence = get_successful_evidence(evidence_list)

    if not successful_evidence:
        return None

    best_evidence = successful_evidence[0]

    for evidence in successful_evidence[1:]:
        current_quality = get_evidence_quality(evidence, evaluation)
        best_quality = get_evidence_quality(best_evidence, evaluation)

        if QUALITY_RANK[current_quality] > QUALITY_RANK[best_quality]:
            best_evidence = evidence

        elif (
            QUALITY_RANK[current_quality] == QUALITY_RANK[best_quality]
            and evidence["year"] > best_evidence["year"]
        ):
            best_evidence = evidence

    return best_evidence

def get_evidence_quality(evidence, evaluation):
    #finds corresponding entry in source_qualities
    for quality_info in evaluation["source_qualities"]:
        if (
            quality_info["publisher"] == evidence["publisher"]
            and quality_info["provenance"] == evidence["provenance"]
        ):
            return quality_info["quality"]

    return "unknown"


if __name__ == '__main__':
    ...