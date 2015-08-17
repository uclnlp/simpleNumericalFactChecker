'''

This script reads in parsed and NER'ed JSONs by Stanford CoreNLP and produces the following structure:

Location:[dep1:[val1, val2], dep1:[val1, val2, ...]]


'''

import json
import sys
import os
import glob
import networkx
import re
import copy
import numpy
import codecs

# this class def allows us to write:
#print(json.dumps(np.arange(5), cls=NumPyArangeEncoder))
#class NumPyArangeEncoder(json.JSONEncoder):
#    def default(self, obj):
#        if isinstance(obj, numpy.ndarray):
#            return obj.tolist() # or map(int, obj)
#        return json.JSONEncoder.default(self, obj)



def getNumbers(sentence):
    # a number can span over multiple tokens
    tokenIDs2number = {}
    for idx, token in enumerate(sentence["tokens"]):
        # avoid only tokens known to be dates or part of locations
        # This only takes actual numbers into account thus it ignores things like "one million"
        # and also treating "500 millions" as "500"
        if token["ner"] not in ["DATE", "LOCATION", "PERSON", "ORGANIZATION", "MISC"]:
            try:
                # this makes sure that 123,123,123.23 which fails the float test, becomes 123123123.23 which is good
                tokenWithoutCommas = re.sub(",([0-9][0-9][0-9])", "\g<1>", token["word"])
                number = float(tokenWithoutCommas)
                # we want this to avoid taking in nan, inf and -inf as floats
                if numpy.isfinite(number):
                    ids = [idx]
                    # check the next token if it is million or thousand
                    if len(sentence["tokens"]) > idx+1:
                        if sentence["tokens"][idx+1]["word"].startswith("trillion"):
                            number = number * 1000000000000
                            ids.append(idx+1)                        
                        elif sentence["tokens"][idx+1]["word"].startswith("billion"):
                            number = number * 1000000000
                            ids.append(idx+1)
                        elif sentence["tokens"][idx+1]["word"].startswith("million"):
                            number = number * 1000000
                            ids.append(idx+1)
                            #print sentence["tokens"]
                            #print number
                        elif sentence["tokens"][idx+1]["word"].startswith("thousand"):
                            number = number * 1000
                            ids.append(idx+1)       
                            #print sentence["tokens"]
                            #print number

                    tokenIDs2number[tuple(ids)] = number          
                    
            except ValueError:
                pass
    return tokenIDs2number

# this function performs a dictNER matching to help with names that Stanford NER fails
# use with caution, it ignores everything apart from the tokens, over-writing existing NER tags 
def dictLocationMatching(sentence, tokenizedLocations):
    # first re-construct the sentence as a string
    wordsInSentence = [] 
    for token in sentence["tokens"]:
        wordsInSentence.append(token["word"])
    #print wordsInSentence
    for tokLoc in tokenizedLocations:
        #print wordsInSentence
        #print tokLoc
        tokenSeqs = [(i, i+len(tokLoc)) for i in range(len(wordsInSentence)) if wordsInSentence[i:i+len(tokLoc)] == tokLoc]
        #print tokenSeqs
        for tokenSeq in tokenSeqs:
            for tokenNo in range(tokenSeq[0], tokenSeq[1]):
                sentence["tokens"][tokenNo]["ner"]  = "LOCATION"

def getLocations(sentence):
    # note that a location can span multiple tokens
    tokenIDs2location = {}
    currentLocation = []
    for idx, token in enumerate(sentence["tokens"]):
        # if it is a location token add it:
        if token["ner"] == "LOCATION":
            currentLocation.append(idx)
        # if it is a no location token
        else:
            # check if we have just finished a location             
            if len(currentLocation) > 0:
                # convert the tokenID to a tuple (immutable) and put the name there
                locationTokens = []
                for locIdx in currentLocation:
                    locationTokens.append(sentence["tokens"][locIdx]["word"]) 

                tokenIDs2location[tuple(currentLocation)] = " ".join(locationTokens)
                currentLocation = []
                
    return tokenIDs2location

def buildDAGfromSentence(sentence):
    sentenceDAG = networkx.DiGraph()
    for idx, token in enumerate(sentence["tokens"]):
        sentenceDAG.add_node(idx, word=token["word"])
        sentenceDAG.add_node(idx, lemma=token["lemma"])
        sentenceDAG.add_node(idx, ner=token["ner"])        
        sentenceDAG.add_node(idx, pos=token["pos"])

    # and now the edges:
    for dependency in sentence["dependencies"]:
        sentenceDAG.add_edge(dependency["head"], dependency["dep"], label=dependency["label"])
        # add the reverse if one doesn't exist
        # if an edge exists, the label gets updated, thus the standard edges do 
        if not sentenceDAG.has_edge(dependency["dep"], dependency["head"]):
            sentenceDAG.add_edge(dependency["dep"], dependency["head"], label="-" + dependency["label"])
    return sentenceDAG
            
# getDepPaths
# also there can be more than one paths
def getShortestDepPaths(sentenceDAG, locationTokenIDs, numberTokenIDs):
    shortestPaths = []
    for locationTokenID in locationTokenIDs:
        for numberTokenID in numberTokenIDs:
            try:
                # get the shortest paths
                # get the list as it they are unlikely to be very many and we need to len()                  
                tempShortestPaths = list(networkx.all_shortest_paths(sentenceDAG, source=locationTokenID, target=numberTokenID))
                # if the paths found are shorter than the ones we had (or we didn't have any)
                if (len(shortestPaths) == 0) or len(shortestPaths[0]) > len(tempShortestPaths[0]):
                    shortestPaths = tempShortestPaths
                # if they have equal length add them
                elif  len(shortestPaths[0]) == len(tempShortestPaths[0]):
                    shortestPaths.extend(tempShortestPaths)
            # if not paths were found, do nothing
            except networkx.exception.NetworkXNoPath:
                pass
    return shortestPaths

# given the a dep path defined by the nodes, get the string of the lexicalized dep path, possibly extended by one more dep
def depPath2StringExtend(sentenceDAG, path, locationTokenIDs, numberTokenIDs, extend=True):
    strings = []
    # this keeps the various bits of the string
    pathStrings = []
    # get the first dep which is from the location
    pathStrings.append("LOCATION_SLOT~" + sentenceDAG[path[0]][path[1]]["label"])
    # for the words in between add the lemma and the dep
    hasContentWord = False
    for seqOnPath, tokenId in enumerate(path[1:-1]):
        if sentenceDAG.node[tokenId]["ner"] == "O":
            pathStrings.append(sentenceDAG.node[tokenId]["word"].lower() + "~" + sentenceDAG[tokenId][path[seqOnPath+2]]["label"])
            if sentenceDAG.node[tokenId]["pos"][0] in "NVJR":
                hasContentWord = True
        else:
            pathStrings.append(sentenceDAG.node[tokenId]["ner"] + "~" + sentenceDAG[tokenId][path[seqOnPath+2]]["label"])
    
    pathStrings.append("NUMBER_SLOT")
    
    if hasContentWord:
        strings.append("+".join(pathStrings))
                        
    if extend:
        # create additional paths by adding all out-edges from the number token (except for the ones on the path)        
        # the extension is always added left of the node
        for nodeOnPath in path:
            # go over each node on the path
            outEdges = sentenceDAG.out_edges_iter([nodeOnPath])
                                    
            for pathIdx, edge in enumerate(outEdges):
                tempPathStrings = copy.deepcopy(pathStrings)
                # the source of the edge we knew
                curNode, outNode = edge
                # if we are not going on the path
                if outNode not in path and outNode not in numberTokenIDs:
                    if sentenceDAG.node[outNode]["ner"] == "O":
                        if hasContentWord or sentenceDAG.node[outNode]["pos"][0] in "NVJR":
                            #print "*extend*" + sentenceDAG.node[outNode]["lemma"] + "~" + sentenceDAG[curNode][outNode]["label"]
                            #print pathStrings.insert(pathIdx, "*extend*" + sentenceDAG.node[outNode]["lemma"] + "~" + sentenceDAG[curNode][outNode]["label"])
                            tempPathStrings.insert(pathIdx, "*extend*" + sentenceDAG.node[outNode]["word"].lower() + "~" + sentenceDAG[curNode][outNode]["label"])
                            #print tempPathStrings
                            strings.append("+".join(tempPathStrings))
                    elif hasContentWord: 
                        tempPathStrings.insert(pathIdx, "*extend*" + sentenceDAG.node[outNode]["ner"] + "~" + sentenceDAG[curNode][outNode]["label"])
                        strings.append("+".join(tempPathStrings))
                
                
#         # create additional paths by adding all out-edges from the number token (except for the one taking as back)
#         # the number token is the last one on the path
#         #outEdgesFromNumber = sentenceDAG.out_edges_iter([path[-1]])
#         #for edge in outEdgesFromNumber:
#             # the source of the edge we knew
#             dummy, outNode = edge
#             # if we are not going back
#             if outNode != path[-2] and outNode not in numberTokenIDs:
#                 if sentenceDAG.node[outNode]["ner"] == "O":
#                     if hasContentWord or  sentenceDAG.node[outNode]["pos"][0] in "NVJR":
#                         strings.append("+".join(pathStrings + ["NUMBER_SLOT~" + sentenceDAG[path[-1]][outNode]["label"] + "~" + sentenceDAG.node[outNode]["lemma"] ]))
#                 elif hasContentWord: 
#                     strings.append("+".join(pathStrings + ["NUMBER_SLOT~" + sentenceDAG[path[-1]][outNode]["label"] + "~" + sentenceDAG.node[outNode]["ner"] ]))
#         
#         # do the same for the LOCATION
#         outEdgesFromLocation = sentenceDAG.out_edges_iter([path[0]])
#         for edge in outEdgesFromLocation:
#             # the source of the edge we knew
#             dummy, outNode = edge
#             # if we are not going on the path
#             if outNode != path[1] and outNode not in locationTokenIDs:
#                 if sentenceDAG.node[outNode]["ner"] == "O":
#                     if hasContentWord or  sentenceDAG.node[outNode]["pos"][0] in "NVJR":
#                         strings.append("+".join([sentenceDAG.node[outNode]["lemma"] + "~"+ sentenceDAG[path[0]][outNode]["label"]] + pathStrings + ["NUMBER_SLOT"]))
#                 elif hasContentWord:
#                     strings.append("+".join([sentenceDAG.node[outNode]["ner"] + "~"+ sentenceDAG[path[0]][outNode]["label"]] + pathStrings + ["NUMBER_SLOT"]))
#         
        
    return strings

def getSurfacePatternsExtend(sentence, locationTokenIDs, numberTokenIDs, extend=True):
    # so this can go either from the location to the number, or the other way around
    # if the number token is before the first token of the location
    tokenSeqs = []
    if numberTokenIDs[-1] < locationTokenIDs[0]:
        tokenIDs = range(numberTokenIDs[-1]+1, locationTokenIDs[0])
    else:
        tokenIDs = range(locationTokenIDs[-1]+1, numberTokenIDs[0])
    
    # check whether there is a content word: 
    hasContentWord = False
    tokens = []
    for id in tokenIDs:
        if sentence["tokens"][id]["ner"] == "O":
            tokens.append('"' + sentence["tokens"][id]["word"].lower() + '"')
            if sentence["tokens"][id]["pos"][0] in "NVJR":
                hasContentWord = True
        else:
            tokens.append('"' + sentence["tokens"][id]["ner"] + '"')
     
    if numberTokenIDs[-1] < locationTokenIDs[0]:
        tokens = ["NUMBER_SLOT"] + tokens + ["LOCATION_SLOT"]
    else:
        tokens = ["LOCATION_SLOT"] + tokens + ["NUMBER_SLOT"]
    if hasContentWord:
        tokenSeqs.append(tokens)
    
    if extend:
        lhsID = min(list(numberTokenIDs) + list(locationTokenIDs))
        rhsID = max(list(numberTokenIDs) + list(locationTokenIDs))
        # add the word to left
        extension = []
        extensionHasContentWord = False
        for idx in range(lhsID-1, max(-1, lhsID-10),-1):
            if sentence["tokens"][idx]["ner"] == "O":
                extension = ['"' + sentence["tokens"][idx]["word"].lower() + '"']  + extension
                if sentence["tokens"][idx]["pos"][0] in "NVJR":
                    extensionHasContentWord = True
            else:
                extension = ['"' + sentence["tokens"][idx]["ner"] + '"']  + extension
            # add the extension if it has a content word and the last thing added is not a comma    
            if (hasContentWord or extensionHasContentWord) and (sentence["tokens"][idx]["word"] != ","):
                tokenSeqs.append(copy.copy(extension) + tokens)
        
        # and now to the right
        extension = []
        extensionHasContentWord = False
        for idx in range(rhsID+1, min(len(sentence["tokens"]), rhsID+9)):
            if sentence["tokens"][idx]["ner"] == "O":
                extension.append('"' + sentence["tokens"][idx]["word"].lower() + '"')
                if sentence["tokens"][idx]["pos"][0] in "NVJR":
                    extensionHasContentWord = True
            else:
                extension.append('"' + sentence["tokens"][idx]["ner"] + '"')
            # add the extension if it has a content word and the last thing added is not a comma    
            if (hasContentWord or extensionHasContentWord) and (sentence["tokens"][idx]["word"] != ","):    
                tokenSeqs.append(tokens + copy.copy(extension))
            
    return tokenSeqs
    
    
if __name__ == "__main__":
    
    parsedJSONDir = sys.argv[1]
    
    # get all the files
    jsonFiles = glob.glob(parsedJSONDir + "/*.json")
    
    # one json to rule them all
    outputFile = sys.argv[2]
    
    # this forms the columns using the lexicalized dependency and surface patterns
    pattern2location2values = {}
    
    # this keeps the sentences for each pattern
    pattern2sentences = {}
    
    print str(len(jsonFiles)) + " files to process"
    
    # load the hardcoded names (if any):
    tokenizedLocationNames = []
    if len(sys.argv) > 3:
        names = codecs.open(sys.argv[3], encoding='utf-8').readlines()
        for name in names:
            tokenizedLocationNames.append(unicode(name).split())
    print "Dictionary with hardcoded tokenized location names"
    print tokenizedLocationNames
    
    for fileCounter, jsonFileName in enumerate(jsonFiles):
        print "processing " + jsonFileName
        with codecs.open(jsonFileName) as jsonFile:
            parsedSentences = json.loads(jsonFile.read())
        
        for sentence in parsedSentences:
            # fix the ner tags
            if len(tokenizedLocationNames)>0:
                dictLocationMatching(sentence, tokenizedLocationNames)
            
            tokenIDs2number = getNumbers(sentence)
            tokenIDs2location = getLocations(sentence)
            
            # if there was at least one location and one number build the dependency graph:
            if len(tokenIDs2number) > 0 and len(tokenIDs2location) > 0 and len(sentence["tokens"])<120:
                
                sentenceDAG = buildDAGfromSentence(sentence)
                
                wordsInSentence = [] 
                for token in sentence["tokens"]:
                    wordsInSentence.append(token["word"])
                sample = " ".join(wordsInSentence)
    
                # for each pair of location and number 
                # get the pairs of each and find their dependency paths (might be more than one) 
                for locationTokenIDs, location in tokenIDs2location.items():
    
                    for numberTokenIDs, number in tokenIDs2number.items():
    
                        # keep all the shortest paths between the number and the tokens of the location
                        shortestPaths = getShortestDepPaths(sentenceDAG, locationTokenIDs, numberTokenIDs)
                        
                        # ignore paths longer than some number deps (=tokens_on_path + 1)
                        if len(shortestPaths) > 0 and len(shortestPaths[0]) < 10:
                            for shortestPath in shortestPaths:
                                pathStrings = depPath2StringExtend(sentenceDAG, shortestPath, locationTokenIDs, numberTokenIDs)
                                for pathString in pathStrings:
                                    if pathString not in pattern2location2values:
                                        pattern2location2values[pathString] = {}
                                        
                                
                                    if location not in pattern2location2values[pathString]:
                                        pattern2location2values[pathString][location] = []
                            
                                    pattern2location2values[pathString][location].append(number)
                                    if pathString in pattern2sentences:
                                        pattern2sentences[pathString].append(sample)
                                    else:
                                        pattern2sentences[pathString] = [sample]
                                    
                        # now get the surface strings 
                        surfacePatternTokenSeqs = getSurfacePatternsExtend(sentence, locationTokenIDs, numberTokenIDs)   
                        for surfacePatternTokens in surfacePatternTokenSeqs:
                            if len(surfacePatternTokens) < 15:
                                surfaceString = ",".join(surfacePatternTokens)
                                if surfaceString not in pattern2location2values:
                                    pattern2location2values[surfaceString] = {}
                                    
                                    
                                if location not in pattern2location2values[surfaceString]:
                                    pattern2location2values[surfaceString][location] = []
                            
                                pattern2location2values[surfaceString][location].append(number)

                                if surfaceString in pattern2sentences:
                                    pattern2sentences[surfaceString].append(sample)
                                else:
                                    pattern2sentences[surfaceString] = [sample]
                                        
        # save every 1000 files
        if fileCounter % 10000 == 0:
            print str(fileCounter) + " files processed"   
            with open(outputFile + "_tmp", "wb") as out:
                json.dump(pattern2location2values, out)
    
            with open(outputFile + "_sentences_tmp", "wb") as out:
                json.dump(pattern2sentences, out)
            
                            
    with open(outputFile, "wb") as out:
        json.dump(pattern2location2values, out)
    
    with open(outputFile + "_sentences", "wb") as out:
        json.dump(pattern2sentences, out)
    
        
