from config import (
    MAX_ACCEPTABLE_DISAGREEMENT,
    HIGH_DISAGREEMENT,
    MAX_RECENT_AGE
)
from evaluation import get_successful_evidence
import os
from dotenv import load_dotenv
import anthropic

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

def reconcile_evidence(country_name, evidence_list, evaluation):
    confidence = calculate_confidence(evaluation)
    best_evidence = choose_best_evidence(evidence_list, evaluation)
    if best_evidence is None:
        return {
            "country": country_name,
            "population": None,
            "year": None,
            "publisher": None,
            "confidence": "low",
            "source_quality": None,
            "explanation": "No successful evidence was available"
        }

    
    explanation = generate_final_explanation(country_name, best_evidence, confidence,
    evidence_list, evaluation)

    return {
        "country": country_name,
        "population": best_evidence["population"],
        "year": best_evidence["year"],
        "publisher": best_evidence["publisher"],
        "confidence": confidence,
        "source_quality": get_evidence_quality(best_evidence, evaluation),
        "explanation": explanation
    }

def generate_final_explanation(country_name, best_evidence, confidence, evidence_list, evaluation):
    prompt = f"""
    You are explaining the result of a population fact reconciliation system.
    The system has already made these deterministic decisions:

    Country: {country_name}
    Selected best evidence: {best_evidence}
    Confidence: {confidence}
    All retrieved evidence: {evidence_list}
    Evaluation: {evaluation}

    Your task:
    - explain why the selected evidence is the best-supported answer
    - explain meaningful disagreements between sources
    - mention stale evidence where relevant
    - mention failed retrievals where relevant
    - mention provenance limitations where relevant
    - explain why the confidence level is appropriate
    Use only the supplied evidence and evaluation fields.
    Do not add qualitative claims such as "gold-standard", "normal",
    "industry-standard", or methodological explanations unless those are
    explicitly supported by the supplied data.
    Do not describe sources as independent if the evaluation reports
    shared or duplicate provenance.
    Do not change the selected population value.
    Do not change the confidence level.
    Do not introduce facts that are not present in the supplied evidence.
    Keep the explanation concise. Keep the explanation under 120 words.
    """

    load_dotenv()

    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        timeout=15.0
    )

    try:
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return message.content[0].text
    except anthropic.AnthropicError:
        return (
            f"The selected estimate is {best_evidence['population']} "
            f"for {best_evidence['year']} from {best_evidence['publisher']}. "
            f"Confidence is {confidence}. "
            "A detailed semantic explanation could not be generated."
        )
