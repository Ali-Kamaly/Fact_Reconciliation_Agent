import requests
API_RETRIEVAL_TYPE = "api"
API_PUBLISHER = "World Bank"
#simplification for provenance because World Bank population data
#can itself incorporate underlying statistical sources
API_PROVENANCE = "World Bank"
API_URL = "https://api.worldbank.org/v2/"

def get_wb_population(country_code):
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/SP.POP.TOTL"
    response = requests.get(
        url,
        params = {"format": "json"}
    ).json()

    last_updated = response[0]['lastupdated']
    #making sure latest valid population value is found
    for record in response[1]:
        if record['value'] is not None:
            population = int(record['value'])
            year = int(record['date'])
            break

    return {
        "retrieval_type": API_RETRIEVAL_TYPE,
        "population": population,
        "year": year,
        "publisher": API_PUBLISHER,
        "provenance": API_PROVENANCE,
        "url": API_URL,
        "last_updated": last_updated,
        "status": "success",
        "error": None
    }

if __name__ == "__main__":
    #standardise using the ISO alpha-3 codes, both api and local database uses it
    print(get_wb_population("BGD"))