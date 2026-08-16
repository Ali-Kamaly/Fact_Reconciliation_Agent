from datetime import datetime

def get_successful_evidence(evidence_list):
    return [evidence for evidence in evidence_list if evidence['status'] == 'success']

def get_data_age(evidence):
    current_year = datetime.now().year
    return current_year - evidence['year']

def check_provenance_independence(evidence_list):
    provenance_groups = {}

    for evidence in evidence_list:
        #will need to improve canonicalisation later - v1
        provenance = evidence['provenance'].strip().lower()
        if provenance not in provenance_groups:
            provenance_groups[provenance] = []
        provenance_groups[provenance].append(evidence)

    duplicates = {
        provenance: evidence_group
        for provenance, evidence_group in provenance_groups.items()
        if len(evidence_group)>1
    }

    return duplicates