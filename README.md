# Simple Numerical Fact-Checker
Fact checker for simple claims about statistical properties

This repository contains the code and data needed to reproduce the results of the paper:

Identification and Verification of Simple Claims about Statistical Properties

Andreas Vlachos and Sebastian Riedel, EMNLP 2015

Preprocessing:

1. FreeBaseDownload.py: to get the JSONs for all statistical regions in FreeBase.
2. numberExtraction.py: to extract the most recent numbers mentioned for each statistical region in a triple form: region-property-value
3. dataFiltering.py: to get the countries and properties with most values filled in (2 parameters to play with). From this we get the file data/allCountriesPost2010-2014Filtered15-150.json.
4. bingDownload.py: to run queries of the form "region + property" on Bing and get JSONs back with the links
5. htmlDownload.py: to get the html from the links
6. obtainAliases.py: Gets the common aliases for the statistical regions considered needed for the matrix filtering later on. From this we get the file data/aliases.json.

Then we run the following bits of Java from the HTML2Stanford:
HTML2Text (need the BoilerPipe jar)
Text2Parsed2JSON (careful to use the CollapsedCCproccessed dependencies, best a more recent version of Stanford CoreNLP (>3.5) that outputs straight to json) 

From this we obtain a large number of html pages, converted to text, parsed with Stanford CoreNLP.

And then:

1. buildMatrix.py: This processes the preprocessed HTML pages and builds a json file which is a dictionary from pattern (string or lexicalized dependencies) to countries/locations and then to the values.
2. matrixFiltering.py: this takes the matrix from the previous step and filters its values and patterns to avoid those without enough entries or those whose entries have too much deviation so they cannot be sensibly averaged. Also uses the aliases to merge the values for different location names used in the experiments. From this we get the file data/theMatrixExtend120TokenFiltered_2_2_0.1_0.5_fixed2.json.

3. Split the data from Freebase (data/allCountriesPost2010-2014Filtered15-150.json) into training/dev (data/train.json) and test (data/test.json).

4. To reproduce the IE-style evaluation results

- informedGuess: 
  
```python src/main/fixedValuePredictor.py data/train.json data/theMatrixExtend120TokenFiltered_2_2_0.1_0.5_fixed2.json data/test.json out/informedGuess```

- unadjustedMAPE:

```python src/main/baselinePredictor.py data/train.json data/theMatrixExtend120TokenFiltered_2_2_0.1_0.5_fixed2.json data/test.json out/unadjustedMAPE FALSE```

- adjustedMAPE:

```python src/main/baselinePredictor.py data/train.json data/theMatrixExtend120TokenFiltered_2_2_0.1_0.5_fixed2.json data/test.json out/adjustedMAPE TRUE```

To run the fact-checker on the HTML pages obtained from the web:

First create a directory for the output, i.e.:

```mkdir out```

Then run

```python src/main/factChecker.py data/allCountriesPost2010-2014Filtered15-150.json data/theMatrixExtend120TokenFiltered_2_2_0.1_0.5_fixed2.json population 0.03125 data/htmlPages2textPARSEDALL data/locationNames data/aliases.json out/population.tsv```

The directory data/htmlPages2textPARSEDALL is not on github due to its size (1.6GB compressed), but feel free to ask me for it.

This is run for each of the 16 properties independently. The parameter for adjusted MAPE used in the paper was set according to the IE experiments. Here is the table the setting for each property:

- gni_per_capita_in_ppp_dollars: 8
- gdp_nominal: 0.03125
- internet_users_percent_population: 2
- cpi_inflation_rate: 2
- health_expenditure_as_percent_of_gdp: 2
- gdp_growth_rate: 1
- fertility_rate: 0.5
- consumer_price_index: 1
- prevalence_of_undernourisment: 32
- gni_in_ppp_dollars: 16
- population_growth_rate: 0.0078125
- diesel_price_liter: 2
- life_expectancy: 1
- population: 0.03125
- gdp_nominal_per_capita: 16
- renewable_freshwater_per_capita: 8

The output for each relation is a .tsv file which can be loaded in Excel. We did this and labeled the claims. The files from which the results in Table 2 are obtained are in data/labeled_claims.
