'''
Created on May 10, 2014

@author: andreasvlachos

This script downloads all statistical regions from FreeBase using a combination of the MQL read API and the Topic API.
'''
import json
import urllib

# TODO: add the part to retrieve the aliases:
# [{ "mid": null, "name": null, "/common/topic/alias": [], "type": "/location/statistical_region", "limit": 100 }]

api_key =  open("/cs/research/intelsys/home1/avlachos/freebaseApiKey").read()
mqlread_url = 'https://www.googleapis.com/freebase/v1/mqlread'
# use the mid instead of the id as they do need escaping
mql_query = '[{"mid": null,"name": null, "type": "/location/statistical_region","limit": 100}]'
# set this to the last value we obtained
cursor = ""

# we need to have a parameter limit=0 as in:
topicService_url = 'https://www.googleapis.com/freebase/v1/topic'
params = {
  'key': api_key,
  'filter': '/location/statistical_region',
  'limit': 0
}

# Given the quota, we can run this 1000 times daily.
# It stops when the topics are exhausted.

for i in xrange(1000):
    # construct the query
    mql_url = mqlread_url + '?query=' + mql_query + "&cursor=" + cursor
    print mql_url
    statisticalRegionsResult = json.loads(urllib.urlopen(mql_url).read())
    #print statisticalRegionsResult
    for region in statisticalRegionsResult["result"]:
        print region["mid"]# + ":" + region["name"]
        # now get the statistical properties
        topic_url = topicService_url + region["mid"] + '?' + urllib.urlencode(params)
        topicResult = json.loads(urllib.urlopen(topic_url).read())
        # print topicResult
        topicResult["name"] = region["name"]
        filename = region["mid"].split("/")[-1] + ".json"
        with open(filename, 'w') as outfile:
            json.dump(topicResult, outfile)

    # update the cursor
    cursor = statisticalRegionsResult['cursor']
    # this cursor can be used to resume the data download
    print "New cursor to process"
    print cursor
    if not cursor:
        break
