from tools.local_population import get_local_population
from tools.web_population import get_web_population
from tools.world_bank import get_wb_population
from evaluation import evaluate_evidence
from config import (
    MAX_RETRIEVAL_COUNT,
    MAX_SOURCE_ATTEMPTS,
    MAX_ACCEPTABLE_DISAGREEMENT,
    MAX_RECENT_AGE
)
from reconciliation import reconcile_evidence

def run_agent(country_name, country_code):
    evidence_list = []
    excluded_urls = []
    retrieval_count = 0

    attempt_counts = {
        "local_file": 0,
        "api": 0,
        "web_search": 0
    }

    #force agent to first try to get local, api & web first iteration
    print(f"[AGENT]\nAction: Getting initial local data")
    local = get_local_population(country_code)
    evidence_list.append(local)
    attempt_counts['local_file']+=1
    retrieval_count+=1

    print(f"[AGENT]\nAction: Getting initial API data")
    api = get_wb_population(country_code)
    evidence_list.append(api)
    attempt_counts['api']+=1
    retrieval_count+=1

    print(f"[AGENT]\nAction: Getting initial web data")
    web = get_web_population(country_name)
    evidence_list.append(web)
    attempt_counts['web_search']+=1
    retrieval_count+=1
    if web['url']:
        excluded_urls.append(web['url'])

    #calculating evaluaiton before loop for robustness
    evaluation = evaluate_evidence(evidence_list)

    #adaptive phase
    while retrieval_count<MAX_RETRIEVAL_COUNT:

        decision = choose_next_action(evidence_list, attempt_counts, evaluation)
        action, reason = decision['action'], decision['reason']

        print(f"[AGENT]\nAction: {action}\nReason: {reason}")
        if action == 'finish':
            break

        #agent will retry same source only one other time before skipping it if both times retrieval fails
        if action == 'local_file':
            result = get_local_population(country_code)
            
        elif action == 'api':
            result = get_wb_population(country_code)
                        
        elif action == 'web_search':
            result = get_web_population(country_name, excluded_urls)

            if result['url']:
                excluded_urls.append(result['url'])

        evidence_list.append(result)

        retrieval_count +=1
        attempt_counts[action]+=1
        evaluation = evaluate_evidence(evidence_list)


    #only prints if max retrieval count reached
    else:
        print(f"[AGENT]\nAction: Finish\nReason: Max retrieval count of {MAX_RETRIEVAL_COUNT} has been reached")

    final_answer = reconcile_evidence(country_name, evidence_list, evaluation)

    return {
        "answer": final_answer,
        "evidence": evidence_list,
        "evaluation": evaluation
    }

def evidence_is_sufficient(evaluation):
    if evaluation['successful_source_count'] <3:
        return False
    if evaluation['unique_known_provenance_count'] < 3:
        return False
    if evaluation['max_pairwise_difference']>MAX_ACCEPTABLE_DISAGREEMENT:
        return False
    has_recent_source = any(
        source['age'] <= MAX_RECENT_AGE for source in evaluation['source_ages']
    )
    if not has_recent_source:
        return False

    return True

def choose_next_action(evidence_list, attempt_counts, evaluation):
    successful_types = [evidence["retrieval_type"] for evidence in evidence_list if evidence["status"] == "success"]

    if 'local_file' not in successful_types and attempt_counts['local_file'] < MAX_SOURCE_ATTEMPTS: 
        return {
            "action": "local_file",
            "reason": "retrying, initial local file retrieval failed"
        }

    if 'api' not in successful_types and attempt_counts['api'] < MAX_SOURCE_ATTEMPTS:
        return {
            "action": "api",
            "reason": "retrying, initial api retrieval failed"
            }

    if 'web_search' not in successful_types and attempt_counts['web_search'] < MAX_SOURCE_ATTEMPTS:
        return {
            "action": "web_search",
            "reason": "retrying, initial web search retrieval failed"
            }

    if not evidence_is_sufficient(evaluation) and attempt_counts['web_search'] < MAX_SOURCE_ATTEMPTS:
        return {
            "action": "web_search",
            "reason": "current evidence is insufficient; seeking additional web evidence"
        }

    if evidence_is_sufficient(evaluation):
        return {
        "action": "finish",
        "reason": "current evidence is sufficient"
    }

    return {
        "action": "finish",
        "reason": (
            "current evidence is still insufficient but no useful retrieval actions "
            "remain within source retry limits"
        )
    }
