# -*- coding: utf-8 -*-


import sys
import unicodedata
import codecs
import json

import os.path
import os

import glob

import urllib2

# this is the directory
jsonDirName = sys.argv[1]

# get all the files
jsonFiles = glob.glob(jsonDirName + "/*")

outputPathName = sys.argv[2]

if not os.path.exists(outputPathName):
    print "creating dir"
    os.mkdir(outputPathName)

urls_processed = []
for jsonFile in jsonFiles:
    # get the name of the directory
    print "processing file " + jsonFile
    jsonName = os.path.basename(jsonFile)
        
    # load the json with the results
    with open(jsonFile) as dataFile:
        bingResults = json.loads(dataFile.read())

    for result in bingResults:

        # get the url:
        url = result["Url"]

        url = url.encode('utf-8')
        #print url
        # avoid processing the same page multiple times
        if url not in urls_processed:
            urls_processed.append(url)
            local_filename = os.path.join(outputPathName, url.replace('/', '|').decode('utf-8'))
            # build a request to fetch the html:
            req = urllib2.Request(url, headers={'User-Agent' : "NumberMatrixCompletion (https://sites.google.com/site/andreasvlachos/resources)"})
            try:
                # fetch the html with time limit 30s
                page = urllib2.urlopen(req, None, 30)
                # save it in a UTF8 file
                local_file = codecs.open(local_filename, encoding='utf-8', mode="w")
                content = page.read()
                ucontent = ""
                try:
                    ucontent = unicode(content, 'utf-8')
                except UnicodeDecodeError:
                    ucontent = unicode(content, 'latin-1')
                local_file.write(ucontent)
                local_file.close()                        

            except:
                print url + '\tERROR:' + str(sys.exc_info()[0])
