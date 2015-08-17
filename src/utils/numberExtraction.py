'''
Created on May 10, 2014

@author: andreasvlachos

This script takes jsons downloaded from Freebase, one for each statistical region and extracts all 2010 or later statistics.

'''

propertyTypes2ValueTime = {
                        "/measurement_unit/dated_integer":["/measurement_unit/dated_integer/number", "/measurement_unit/dated_integer/year"],\
                        "/measurement_unit/dated_money_value":["/measurement_unit/dated_money_value/amount", "/measurement_unit/dated_money_value/valid_date"],\
                        "/location/co2_emission":["/location/co2_emission/emissions","/location/co2_emission/date"],\
                        "/measurement_unit/dated_float":["/measurement_unit/dated_float/number","/measurement_unit/dated_float/date"],\
                        "/location/oil_production":["/location/oil_production/oil_produced","/location/oil_production/date"],\
                        "/location/natural_gas_production":["/location/natural_gas_production/natural_gas_produced","/location/natural_gas_production/date"],\
                        "/location/electricity_production":["/location/electricity_production/electricity_produced","/location/electricity_production/date"],\
                        "/measurement_unit/dated_percentage":["/measurement_unit/dated_percentage/rate","/measurement_unit/dated_percentage/date"],\
                        "/measurement_unit/recurring_money_value":["/measurement_unit/recurring_money_value/amount","/measurement_unit/recurring_money_value/date"],\
                        "/measurement_unit/dated_metric_ton":["/measurement_unit/dated_metric_ton/number","/measurement_unit/dated_metric_ton/date"],\
                        "/measurement_unit/dated_kgoe":["/measurement_unit/dated_kgoe/number","/measurement_unit/dated_kgoe/date"], \
                        "/measurement_unit/dated_kilowatt_hour":["/measurement_unit/dated_kilowatt_hour/number","/measurement_unit/dated_kilowatt_hour/date"],\
                        "/measurement_unit/dated_money_value":["/measurement_unit/dated_money_value/amount","/measurement_unit/dated_money_value/valid_date"],\
                        "/measurement_unit/adjusted_money_value":["/measurement_unit/adjusted_money_value/adjusted_value","/measurement_unit/adjusted_money_value/measurement_date"],\
                        "/measurement_unit/dated_metric_tons_per_million_ppp_dollars":["/measurement_unit/dated_metric_tons_per_million_ppp_dollars/emission_intensity_value","/measurement_unit/dated_metric_tons_per_million_ppp_dollars/date"],\
                        "/measurement_unit/dated_cubic_meters":["/measurement_unit/dated_cubic_meters/cubic_meters", "/measurement_unit/dated_cubic_meters/date"],\
                        "/measurement_unit/dated_days":["/measurement_unit/dated_days/days","/measurement_unit/dated_days/date"],\
                        "/measurement_unit/dated_index_value":["/measurement_unit/dated_index_value/index_value","/measurement_unit/dated_index_value/date"]
                        }

import json
import os

# given a json extract the most recent numerical value for each of the properties mentioned
def extractNumericalValues(jsonObj, propertiesOfInterest):
    numbers = {}
    country = json.loads(jsonObj)
    if country["name"] == None:
        return None, {}
    name = country["name"].encode('utf-8')
    print name
    # for each property
    # Some countries have nothin in them
    if "property" not in country:
        return name, {}
    for prop, value in country["property"].items():
        # get the name 
        # avoid the religions
        if prop not in propertiesOfInterest:
            continue
        print "Property=" + prop
        expectedType = propertiesOfInterest[prop]["expectedType"]
        valueType, timeType = propertyTypes2ValueTime[expectedType]
        
        # keep the valuetype for this property
        #valueType = value["valuetype"]
        #print valueType
        mostRecentValue = 0.0
        # we represent time as year, month
        mostRecentTime = [0, 0]
        for val in value["values"]:
            #print val["property"].keys()
            thisValue = None
            thisTime = None
            if "property" not in val:
                continue
            if valueType in val["property"] and timeType in val["property"]\
            and len(val["property"][valueType]["values"]) > 0 and len(val["property"][timeType]["values"]) > 0:
                thisValue = val["property"][valueType]["values"][0]["value"]
                thisTime = val["property"][timeType]["values"][0]["value"]
            else:
                continue

            try:
                # if the time is given as YYYY-MM or YYYY-MM-DD                             
                if thisTime.find("-") > -1:
                    if len(thisTime.split("-")) ==2:
                        thisYear, thisMonth = thisTime.split("-")
                        thisTime = [int(thisYear), int(thisMonth)]
                    elif len(thisTime.split("-")) ==3:
                        # the day of the month is ignored
                        thisYear, thisMonth, thisDay = thisTime.split("-")
                        thisTime = [int(thisYear), int(thisMonth)]                        
                else:
                    # or it is just YYYY
                    thisTime = [int(thisTime), 0]
                # check that the numbers are not future projections!
                if (thisTime[0] < 2015) and ((mostRecentTime == [0,0]) or (thisTime[0] > mostRecentTime[0]) \
                    or (thisTime[0] == mostRecentTime[0] and thisTime[1] > mostRecentTime[1])):
                    mostRecentTime = thisTime
                    mostRecentValue = thisValue
            # if the time specified cannot be parsed, ignore it
            except ValueError:
                pass
        # or the time of the measurement is recent enough
        if  mostRecentTime[0] >= 2010:
            print "Time=" + str(mostRecentTime) + " Value=" + str(mostRecentValue)
            numbers[prop] = mostRecentValue
    return name, numbers
    

if __name__ == '__main__':
    import sys
    dirName = sys.argv[1]
    propertiesOfInterest = {}
    with open(dirName + "../propertiesOfInterest.json") as props:
        propertiesOfInterest = json.loads(props.read())

    countries2numbers = {}
    totalCountries = 0
    totalNumbers = 0
    uniqueRelations = []
    relation2counts = {}
    rels = []
    for fl in os.listdir(dirName):
        print fl
        jsonFl = open(dirName + "/" + fl).read()
        name, numbers = extractNumericalValues(jsonFl, propertiesOfInterest)
        if name != None and len(numbers)>0:
            countries2numbers[name] = numbers
            totalCountries += 1
            for relation in numbers:
                totalNumbers += 1
                if relation not in uniqueRelations:
                    uniqueRelations.append(relation)
                    relation2counts[relation] = 0
                relation2counts[relation] += 1
            
    print countries2numbers
    # maybe return a json? Would be useful to be language independent
    print relation2counts
    print "countries with at least one 2010-2014 number: " + str(totalCountries)
    print "total post 2010 numbers: " + str(totalNumbers)
    print "Unique relations: " + str(len(uniqueRelations))    
    
    with open(dirName + "../allCountriesPost2010-2014.json", 'wb') as dc:
        json.dump(countries2numbers, dc)

    
        