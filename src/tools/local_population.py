import pandas as pd

LOCAL_RETRIEVAL_TYPE = "local_file"
LOCAL_PUBLISHER = "Kaggle - World Population Dataset"
#more review needed for kaggle provenance
LOCAL_PROVENANCE = "World Population Review"
LOCAL_URL = "https://www.kaggle.com/datasets/iamsouravbanerjee/world-population-dataset?resource=download"



def get_local_population(country_code):
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
        #change later to match evidence shape
        return None

    for year_population, data_year in population_years:
        population = country_row[year_population].iloc[0]

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

    return None

if __name__ == "__main__":
    print(get_local_population("BGD"))