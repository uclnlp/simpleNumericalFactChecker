'''

Then it trains a model using a matrix of text patterns and database

It then obtains a ranking of the patterns

And the checks files parsed and NER'ed JSONs by Stanford CoreNLP and produces the following structure:

Location:[dep1:[val1, val2], dep1:[val1, val2, ...]]

It produces a ranking of the sentences according to the relation at question and scores each value by MAPE 

'''

import json
import sys
import os
import glob
import codecs
import operator
import buildMatrix
import baselinePredictor



# training data
# load the FreeBase file
with open(sys.argv[1]) as freebaseFile:
    region2property2value = json.loads(freebaseFile.read())
    
# we need to make it property2region2value
property2region2value = {}
for region, property2value in region2property2value.items():
    for property, value in property2value.items():
        if property not in property2region2value:
            property2region2value[property] = {}
        property2region2value[property][region] = value

# text patterns
textMatrix = baselinePredictor.BaselinePredictor.loadMatrix(sys.argv[2]) 

# specify which ones are needed:
property = "/location/statistical_region/" + sys.argv[3]

# first let's train a model

predictor = baselinePredictor.BaselinePredictor()
params = [True, float(sys.argv[4])]

# train
predictor.trainRelation(property, property2region2value[property], textMatrix, sys.stdout, params)

print "patterns kept:"
print predictor.property2patterns[property].keys()


# parsed texts to check
parsedJSONDir = sys.argv[5]

# get all the files
jsonFiles = glob.glob(parsedJSONDir + "/*.json")


print str(len(jsonFiles)) + " files to process"

# load the hardcoded names 
tokenizedLocationNames = []
names = codecs.open(sys.argv[6], encoding='utf-8').readlines()
for name in names:
    tokenizedLocationNames.append(unicode(name).split())
print "Dictionary with hardcoded tokenized location names"
print tokenizedLocationNames

# get the aliases 
# load the file
with open(sys.argv[7]) as jsonFile:
    region2aliases = json.loads(jsonFile.read())

# so we first need to take the location2aliases dict and turn in into aliases to region
alias2region = {} 
for region, aliases in region2aliases.items():
    # add the location as alias to itself
    alias2region[region] = region
    for alias in aliases:
        # so if this alias is used for a different location
        if alias in alias2region and region!=alias2region[alias]:            
            alias2region[alias] = None
            alias2region[alias.lower()] = None
        else:
            # remember to add the lower
            alias2region[alias] = region
            alias2region[alias.lower()] = region
            
# now filter out the Nones
for alias, region in alias2region.items():
    if region == None:
        print "alias ", alias, " ambiguous"
        del alias2region[alias]
        
print alias2region

# store the result: sentence, country, number, nearestPattern, euclidDistance, correctNumber, MAPE

tsv = open(sys.argv[8], "wb")

headers = ['sentence', 'region', 'kb_region', 'property', 'kb_value', 'mape_support_scaling_param', 'pattern', 'value', 'MAPE', 'source_JSON']

tsv.write("\t".join(headers) + "\n")

# Now go over each file
for fileCounter, jsonFileName in enumerate(jsonFiles):
    #print "processing " + jsonFileName
    with codecs.open(jsonFileName) as jsonFile:
        parsedSentences = json.loads(jsonFile.read())
    
    for sentence in parsedSentences:
        # skip sentences with more than 120 tokens.
        if len(sentence["tokens"])>120:
            continue
            
        # fix the ner tags
        if len(tokenizedLocationNames)>0:
            buildMatrix.dictLocationMatching(sentence, tokenizedLocationNames)

        wordsInSentence = [] 
        for idx, token in enumerate(sentence["tokens"]):
            wordsInSentence.append(token["word"])
        
        #print "Sentence: " + sentenceText.encode('utf-8')

        # get the numbers mentioned        
        tokenIDs2number = buildMatrix.getNumbers(sentence)        
        
        # and the locations mentioned in the sentence
        tokenIDs2location = buildMatrix.getLocations(sentence)
        
        # So let's check if the locations are among those that we can fact check for this relation
        for locationTokenIDs, location in tokenIDs2location.items():
            
            # so we have the location, but is it a known region?
            region = location
            # if the location has an alias
            if location in alias2region:
                # get it
                region = alias2region[location]
            elif location.lower() in alias2region:
                region = alias2region[location.lower()]
            
            if region in property2region2value[property]:  
                    
                sentenceDAG = buildMatrix.buildDAGfromSentence(sentence)
                                    
                for numberTokenIDs, number in tokenIDs2number.items():
                    
                    #print "number in text: " + str(number)
                    
                    patterns = []
                    # keep all the shortest paths between the number and the tokens of the location
                    shortestPaths = buildMatrix.getShortestDepPaths(sentenceDAG, locationTokenIDs, numberTokenIDs)
                    for shortestPath in shortestPaths:
                        pathStrings = buildMatrix.depPath2StringExtend(sentenceDAG, shortestPath, locationTokenIDs, numberTokenIDs)
                        patterns.extend(pathStrings)
                                
                    # now get the surface strings 
                    surfacePatternTokenSeqs = buildMatrix.getSurfacePatternsExtend(sentence, locationTokenIDs, numberTokenIDs)
                    for surfacePatternTokens in surfacePatternTokenSeqs:
                        if len(surfacePatternTokens) < 15:
                            surfaceString = ",".join(surfacePatternTokens)
                            patterns.append(surfaceString)

                    patternsApplied = []
                    for pattern in patterns:
                        if pattern in predictor.property2patterns[property].keys():
                            patternsApplied.append(pattern)

                    if len(patternsApplied) > 0:
                        wordsInSentence[numberTokenIDs[0]] = "<number>" + wordsInSentence[numberTokenIDs[0]]
                        wordsInSentence[numberTokenIDs[-1]] = wordsInSentence[numberTokenIDs[-1]] + "</number>" 
                        
                        wordsInSentence[locationTokenIDs[0]] = "<location>" + wordsInSentence[locationTokenIDs[0]]
                        wordsInSentence[locationTokenIDs[-1]] = wordsInSentence[locationTokenIDs[-1]] + "</location>"
                        
                        sentenceText = " ".join(wordsInSentence)
                        
                        print "Sentence: " + sentenceText.encode('utf-8')
                        print "location in text " + location.encode('utf-8') + " is known as " + region.encode('utf-8') + " in FB with known " + property + " value " + str(property2region2value[property][region])
                        print "confidence level= " + str(len(patternsApplied)) + "\t" + str(patternsApplied)
                        print "sentence states that " + location.encode('utf-8') + " has " + property + " value " + str(number)
                        if property2region2value[property][region] != 0.0:
                            mape = abs(number - property2region2value[property][region]) / float(abs(property2region2value[property][region]))
                            print "MAPE: " + str(mape)
                        else:
                            print "MAPE undefined"
                            mape = "undef"
                        print "source: " + jsonFileName
                        print "------------------------------"
                        details = [sentenceText.encode('utf-8'), location.encode('utf-8'), region.encode('utf-8'), sys.argv[3], str(property2region2value[property][region]), str(len(patternsApplied)),str(patternsApplied), str(number), str(mape), jsonFileName]
                        tsv.write("\t".join(details) + "\n")    
                            
tsv.close()                    
                     
                    
                    
                    
    
