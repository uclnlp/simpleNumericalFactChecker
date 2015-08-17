# Following the example from here
# http://www.cs.columbia.edu/~gravano/cs6111/Proj1/bing-python.txt

import urllib2
import base64
import urllib
import json
import os

# from here we only want to keep the countries
with open("/cs/research/intelsys/home1/avlachos/FactChecking/allCountriesPost2010Filtered15-150.json") as dataFile:
    allCountriesData = json.loads(dataFile.read())

# from here get the property ids
with open("/cs/research/intelsys/home1/avlachos/FactChecking/featuresKept.json") as dataFile:
    featuresKept = json.loads(dataFile.read())

# better lowercase the property names
with open("/cs/research/intelsys/home1/avlachos/FactChecking/allStatisticalRegionProperties.json") as dataFile:
    featuresDesc = json.loads(dataFile.read())



propertyKeywords = []
for feature in featuresKept:
    # get the name for it and lower case it
    for feat in featuresDesc["result"]:
        if feat["id"] == feature:
            propertyKeywords.append(feat["name"].lower().encode('utf-8'))
#propertyKeywords = ["fertility rate"]
#print propertyKeywords

countryNames = []
for country in allCountriesData:
    countryNames.append(country.encode('utf-8'))

#countryNames = ["Czech Republic"]
#print countryNames

bingUrl = 'https://api.datamarket.azure.com/Bing/SearchWeb/v1/Web' # ?Query=%27gates%27&$top=10&$format=json'
#Provide your account key here
accountKey = 'ZAk6G5VxGSD+K/mx3QH+PX24x85Cx9lEVnQzXA5H+P0'
accountKeyEnc = base64.b64encode(accountKey + ':' + accountKey)
headers = {'Authorization': 'Basic ' + accountKeyEnc}

pathName = "/cs/research/intelsys/home1/avlachos/FactChecking/Bing"

if not os.path.exists(pathName):
    print "creating dir " + pathName
    os.mkdir(pathName)


for keywords in propertyKeywords:
    print keywords
    # create a directory for the relation
    relPathName = pathName + "/" + keywords
    if not os.path.exists(relPathName):
        print "creating dir " +  relPathName
        os.mkdir(relPathName)
    
    for name in countryNames:
        print name
        params = {
                 #'format': "Json",
                  'Adult': "\'Strict\'",
                  'WebFileType' : "\'HTML\'",
                  }
        # the query terms are done with urllib quote in order to get %20 instead of + (bing likes that instead)
        #print '\''.encode('utf-8') + name + " " + keywords + u' 2014\''.encode('utf-8')
        # one can add in the end this bit 'WebSearchOptions'  : "DisableQueryAlterations"
        #&WebSearchOptions=%27DisableQueryAlterations%27
        # this bit can fetch the second page "$skip=100"
        url = bingUrl + "?Query=" + urllib.quote('\''.encode('utf-8') + name + " " + keywords + '\''.encode('utf-8')) + "&" + urllib.urlencode(params) + "&$format=json"
        print url
        req = urllib2.Request(url, headers = headers)
        response = urllib2.urlopen(req)
        content = json.loads(response.read())
        # content contains the xml/json response from Bing. 
        print content
        # save the json in a file named after the country and the property.        
        filename = relPathName + "/" + name + ".json"
        with open(filename, 'w') as outfile:
            json.dump(content["d"]["results"], outfile)
        
