import pandas as pd

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

    #making sure population years are in descending order
    population_years.sort(key=lambda x: x[1], reverse= True)

    country_row = pop_df[pop_df['CCA3'] == country_code]

    if country_row.empty:
        return None

    for year_population, data_year in population_years:
        population = country_row[year_population].iloc[0]

        if pd.notna(population):
            return {
                    "population": int(population),
                    "year": data_year,
            }

    return None

print(get_local_population("BGD"))