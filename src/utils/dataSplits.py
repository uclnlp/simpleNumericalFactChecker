'''
Here we keep functions for training/test splits ensuring the matrix still has enough in each row and column

'''

import random
import json
import sys

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

trainingPortion = 2.0/3.0

# for each property, pick the trainingPortion, ensuring that all countries are represented
trainMatrix = {}
testMatrix = {}

random.seed(3)

for property, region2value in property2region2value.items(): 
    trainMatrix[property] = {}
    testMatrix[property] = {}
    
    regions = region2value.keys()
    random.shuffle(regions)
    
    for idx, region in enumerate(regions):
        if float(idx+1)/float(len(regions)) <trainingPortion:
            trainMatrix[property][region] = region2value[region]
        else:
            testMatrix[property][region] = region2value[region]
  
with open(sys.argv[2], "wb") as outTrain:
    json.dump(trainMatrix, outTrain)

with open(sys.argv[3], "wb") as outTest:
    json.dump(testMatrix, outTest)
