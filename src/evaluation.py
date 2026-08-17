from datetime import datetime
from dotenv import load_dotenv
import anthropic, os, json

def get_successful_evidence(evidence_list):
    return [evidence for evidence in evidence_list if evidence['status'] == 'success']

def get_data_age(evidence):
    current_year = datetime.now().year
    return current_year - evidence['year']

def count_unknown_provenances(evidence_list):
    count = 0
    for evidence in evidence_list:
        if evidence['provenance'].strip().lower() == 'unknown':
            count += 1
    return count

def normalise_provenance(provenance):
    p = provenance.strip().lower()

    if p == 'unknown':
        return None
    
    if "world population prospects" in p:
        return "un_world_population_prospects"

    if "world bank" in p:
        return "world_bank"

    if "world population review" in p:
        return "world_population_review"

    if "census bureau" in p:
        return "us_census_bureau"

    return p

def check_provenance_independence(evidence_list):
    provenance_groups = {}

    for evidence in evidence_list:
        provenance = normalise_provenance(evidence['provenance'])

        if provenance is None:
            #not grouping unknown provenances together
            continue

        if provenance not in provenance_groups:
            provenance_groups[provenance] = []
        provenance_groups[provenance].append(evidence)

    duplicates = {
        provenance: evidence_group
        for provenance, evidence_group in provenance_groups.items()
        if len(evidence_group)>1
    }

    return provenance_groups, duplicates

def calculate_pairwise_percentage_diff(evidence_list):
    #evidence_list will always be relatively small so time complexity is irrelevant
    #symmetric percentage difference since neither source is automatically 'correct baseline'

    percentage_differences = []
    length = len(evidence_list)

    for i in range(length):
        for j in range(i+1, length):
            evidence_a = evidence_list[i]
            evidence_b = evidence_list[j]

            pop_a = evidence_a['population']
            pop_b = evidence_b['population']

            percentage_diff = (abs(pop_a-pop_b)/((pop_a+pop_b)/2) * 100)
            #list of dictionaries with extra info. for better reasoning for agent
            percentage_differences.append({
                "source_a": evidence_a['publisher'],
                "source_b": evidence_b['publisher'],
                "retrieval_a": evidence_a['retrieval_type'],
                "retrieval_b": evidence_b['retrieval_type'],
                "year_a": evidence_a['year'],
                "year_b": evidence_b['year'],
                "percentage_difference": round(percentage_diff, 2)
            }
            )

    return percentage_differences

def evaluate_source_quality(evidence):
    publisher = (evidence['publisher'] or "").strip().lower()
    provenance = (evidence['provenance'] or "").strip().lower()

    #shouldn't ideally happen
    if publisher == "" and provenance == "":
        return {
            "quality" : "unknown",
            "reason": "No data available on publisher nor provenance"
        }

    #obvious known sources
    if "world bank" in publisher or "world bank" in provenance:
        return {
            "quality": "high",
            "reason": "Known authoritative institutional population-data source"
            }
    if (
        "bureau of statistics" in provenance or "national statistics" in provenance
        or "population division" in provenance or "united nations" in provenance
    ):
        return {
            "quality": "high",
            "reason": "Underlying provenance is an official or authoritative statistical source"
        }
    
    if "kaggle" in publisher or "wikipedia" in publisher: 
        return {
            "quality": "medium",
            "reason": "Secondary dataset distribution platform"
            }

    #only after deterministic checks use Claude
    return classify_source_quality_with_claude(evidence)

def classify_source_quality_with_claude(evidence):
    try:
        load_dotenv()
        client = anthropic.Anthropic(api_key = os.getenv("ANTHROPIC_API_KEY"), timeout=15.0)

        prompt = f"""
        You are evaluating source quality for country population statistics.

        Classify the evidence into exactly one of:

        high:
        - official national statistics agency
        - intergovernmental/statistical institution producing or directly publishing population data
        - primary authoritative population-data source

        medium:
        - established secondary source or aggregator
        - reputable publisher clearly citing an authoritative underlying source

        unknown:
        - authority cannot be confidently determined
        - provenance is missing or unclear
        - source does not fit the above categories

        Publisher: {evidence['publisher']}
        Underlying provenance: {evidence['provenance']}

        Judge the quality of the EVIDENCE SOURCE, not whether the population number itself is correct.
        """

        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens = 150,
            messages =[
                {"role": "user",
                 "content": prompt
                }
            ],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "quality": {
                                "type": "string",
                                "enum": ["high", "medium", "unknown"]
                            },
                            "reason": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "quality",
                            "reason"
                        ],
                        "additionalProperties": False
                    }
                }
            }
        )

        return json.loads(message.content[0].text)
    except anthropic.AnthropicError:
        return {
            "quality": "unknown",
            "reason": "Source quality classification unavailable"
        }

def evaluate_evidence(evidence_list):
    successful_evidence = get_successful_evidence(evidence_list)

    successful_source_count = len(successful_evidence)
    failed_source_count = len(evidence_list) - successful_source_count

    source_ages = []
    source_qualities = []

    for evidence in successful_evidence:
        source_ages.append({
            "publisher": evidence['publisher'],
            "age": get_data_age(evidence)
        })
        quality_result = evaluate_source_quality(evidence)
        source_qualities.append({
            "publisher": evidence['publisher'],
            "provenance": evidence['provenance'],
            "quality": quality_result['quality'],
            "reason": quality_result['reason']
        })


    unknown_provenance_count = count_unknown_provenances(successful_evidence)
    provenance_groups, duplicate_provenances = check_provenance_independence(successful_evidence)
    unique_known_provenance_count = len(provenance_groups)
    pairwise_differences = calculate_pairwise_percentage_diff(successful_evidence)


    if pairwise_differences:
        max_pairwise_difference = max(
            evidence['percentage_difference'] for evidence in pairwise_differences
            )
    else:
        max_pairwise_difference = 0

    return {
        "successful_source_count": successful_source_count,
        "failed_source_count": failed_source_count,
        "source_ages": source_ages,
        "source_qualities": source_qualities,
        "unknown_provenance_count": unknown_provenance_count,
        "duplicate_provenances": duplicate_provenances,
        "unique_known_provenance_count": unique_known_provenance_count,
        "pairwise_differences": pairwise_differences,
        "max_pairwise_difference": max_pairwise_difference
    }

