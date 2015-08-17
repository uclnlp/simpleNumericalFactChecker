import abstractPredictor
import numpy
import heapq

class FixedValuePredictor(abstractPredictor.AbstractPredictor):
    
    def __init__(self):
        # this keeps the median for each relation
        self.property2fixedValue = {}
        
        
    def predict(self, property, region, of=None, useDefault=True):
        if useDefault:
            return self.property2fixedValue[property]
        else:
            return None

    # TODO: remove the textMatrix from the arg list
    def trainRelation(self, property, trainRegion2value, textMatrix, of, params=None): 
        
        # try three options
        candidates = [0, numpy.median(trainRegion2value.values()), numpy.mean(trainRegion2value.values())]
        #print candidates
        bestScore = float("inf")
        bestCandidate = None
        for candidate in candidates:    
            prediction = {}
            for region in trainRegion2value:
                prediction[region] = candidate 
            mape = abstractPredictor.AbstractPredictor.MAPE(prediction, trainRegion2value)
            
            if mape < bestScore:
                bestScore = mape
                bestCandidate = candidate

        if bestCandidate == 0:
            of.write(property + " best value is 0 with score " + str(bestScore) + "\n") 
        elif bestCandidate == numpy.median(trainRegion2value.values()):
            of.write(property + " best value is median (" + str(numpy.median(trainRegion2value.values())) + ") with score " + str(bestScore) + "\n")
        elif bestCandidate == numpy.mean(trainRegion2value.values()):
            of.write(property + " best value is mean (" + str(numpy.mean(trainRegion2value.values())) + ") with score " + str(bestScore) + "\n")                
        self.property2fixedValue[property] = bestCandidate

         
    # TODO: refactor to reuse the above
    def train(self, trainMatrix, textMatrix, params=None): 
        for property, trainRegion2value in trainMatrix.items():
            print property, trainRegion2value
            # try three options
            candidates = [0, numpy.median(trainRegion2value.values()), numpy.mean(trainRegion2value.values())]
            bestScore = float("inf")
            bestCandidate = None
            for candidate in candidates:    
                prediction = {}
                for region in trainRegion2value:
                    prediction[region] = candidate 
                mape = abstractPredictor.AbstractPredictor.MAPE(prediction, trainRegion2value)
                
                if mape < bestScore:
                    bestScore = mape
                    bestCandidate = candidate
                    
            if bestCandidate == 0:
                print property, " best value is 0 with score ", bestScore 
            elif bestCandidate == numpy.median(trainRegion2value.values()):
                print property, " best value is median with score ", bestScore
            elif bestCandidate == numpy.mean(trainRegion2value.values()):
                print property, " best value is mean with score ", bestScore                
            self.property2fixedValue[property] = bestCandidate
                            
                
          
if __name__ == "__main__":
    
    import sys
    import os.path
    import json
    
    fixedValuePredictor = FixedValuePredictor()
    
    trainMatrix = fixedValuePredictor.loadMatrix(sys.argv[1])
    textMatrix = fixedValuePredictor.loadMatrix(sys.argv[2])
    testMatrix = fixedValuePredictor.loadMatrix(sys.argv[3])

    outputFileName = sys.argv[4]
    
    #properties = ["/location/statistical_region/population","/location/statistical_region/gdp_real","/location/statistical_region/cpi_inflation_rate"]
    #properties = ["/location/statistical_region/population"]
    properties = json.loads(open(os.path.dirname(os.path.abspath(sys.argv[1])) + "/featuresKept.json").read())

    property2bestParams = fixedValuePredictor.crossValidate(trainMatrix, textMatrix, 4, properties, outputFileName, [[None]])
    #print "OK"
    
    print property2bestParams
    property2MAPE = {}
    for property in properties:
        paramsStrs = []
        for param in property2bestParams[property]:
            paramsStrs.append(str(param))

        ofn = outputFileName + "_" + property.split("/")[-1] + "_" + "_".join(paramsStrs) + "_TEST"
        a= {}
        fixedValuePredictor.runRelEval(a, property, trainMatrix[property], textMatrix, testMatrix[property], ofn, property2bestParams[property])
        property2MAPE[property] = a.values()[0]
        
    for property in sorted(property2MAPE):
        print property, property2MAPE[property]
    print "avg MAPE:", str(numpy.mean(property2MAPE.values()))
        
