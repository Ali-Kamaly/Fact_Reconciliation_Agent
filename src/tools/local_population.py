import pandas as pd

LOCAL_RETRIEVAL_TYPE = "local_file"
LOCAL_PUBLISHER = "Kaggle - World Population Dataset"
#more review needed for kaggle provenance
LOCAL_PROVENANCE = "World Population Review"
LOCAL_URL = "https://www.kaggle.com/datasets/iamsouravbanerjee/world-population-dataset?resource=download"


def get_local_population(country_code):
    try:
        pop_df = pd.read_csv("data/world_population.csv")

        population_years = []
        pop_len = len('Population')
        for col in pop_df:
            if 'Population' in col:
                try:
                    year = int(col[:-pop_len].strip())
                    population_years.append((col, year))
                except ValueError:
                    #removing 'World Population Percentage' col from population_years
                    pass

        #ensuring population years are in descending order
        population_years.sort(key=lambda x: x[1], reverse= True)

        country_row = pop_df[pop_df['CCA3'] == country_code]

        if country_row.empty:
            raise ValueError(f"No country found for code: {country_code}")

        for year_population, data_year in population_years:
            population = country_row[year_population].iloc[0]

            #if no missing value
            if pd.notna(population):
                return {
                        "retrieval_type": LOCAL_RETRIEVAL_TYPE,
                        "population": int(population),
                        "year": data_year,
                        "publisher": LOCAL_PUBLISHER,
                        "provenance": LOCAL_PROVENANCE,
                        "url": LOCAL_URL,
                        "last_updated": None,
                        "status": "success",
                        "error": None
                }

        raise ValueError(f"No valid population data found for country with code: {country_code}")

    except FileNotFoundError:
        return failed_local_request("Local population CSV could not be found")

    except pd.errors.ParserError as error:
        return failed_local_request(f"Local csv could not be parsed: {error}")

    except KeyError as error:
        return failed_local_request(f"Expected csv column is missing: {error}")

    except ValueError as error:
        return failed_local_request(str(error))


def failed_local_request(error_message):
    return {
        "retrieval_type": LOCAL_RETRIEVAL_TYPE,
        "population": None,
        "year": None,
        "publisher": LOCAL_PUBLISHER,
        "provenance": LOCAL_PROVENANCE,
        "url": LOCAL_URL,
        "last_updated": None,
        "status": "failed",
        "error": error_message
    }

if __name__ == "__main__":
    print(get_local_population("BGD"))
    print(get_local_population("XYZ"))