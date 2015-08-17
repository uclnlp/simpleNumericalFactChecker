'''

This script obtains the aliases from Freebase

'''

import sys
import json
import urllib

# load the file
with open(sys.argv[1]) as freebaseFile:
    region2property2value = json.loads(freebaseFile.read())
    

apiKey = open("/cs/research/intelsys/home1/avlachos/freebaseApiKey").read()    
    
mqlreadUrl = 'https://www.googleapis.com/freebase/v1/mqlread'

aliasQueryParams = {
  'key': apiKey,
}

# the limit gives back only one result, which seems to be the most popular and the one we are interested in 
aliasQuery = { "/common/topic/alias": [], "type": "/location/statistical_region", "limit":1 }

region2aliases = {} 
for regionName in region2property2value:
    print regionName.encode('utf-8')
    aliasQuery["name"] = regionName 
    aliasQueryParams["query"] = json.dumps(aliasQuery)

    aliasUrl = mqlreadUrl + '?' + urllib.urlencode(aliasQueryParams)
    aliasJSON =  json.loads(urllib.urlopen(aliasUrl).read())
    region2aliases[regionName] = aliasJSON["result"]["/common/topic/alias"]
    
with open(sys.argv[2], "wb") as out:
    json.dump(region2aliases, out)

print len(region2aliases), " region names with aliases"
    

