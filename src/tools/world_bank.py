import requests

def get_population(country_code):
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/SP.POP.TOTL"
    response = requests.get(
        url,
        params = {"format": "json"}
    ).json()

    last_updated = response[0]['lastupdated']
    #making sure latest valid population value is found
    for record in response[1]:
        if record['value'] is not None:
            population = record['value']
            year = record['date']
            break

    return {
        "population": population,
        "year": year,
        "last_updated": last_updated
    }

print(get_population("BD"))