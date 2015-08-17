'''
This is a baseline predictor. For each property, it finds the text patterns that correlate the best.
If the value for a country cannot be predicted in this way, it returns the average of the property
'''
import operator
import json
import numpy
import random
from sklearn.metrics import mean_squared_error
import math
import multiprocessing
from collections import OrderedDict


class AbstractPredictor(object):
    def __init__(self):
        pass

    @staticmethod
    def loadMatrix(jsonFile):
        print "loading from file " + jsonFile
        with open(jsonFile) as freebaseFile:
            property2region2value = json.loads(freebaseFile.read())
        

        regions = set([])
        valueCounter = 0
        for property, region2value in property2region2value.items():
            # Check for nan values and remove them
            for region, value in region2value.items():
                if not numpy.isfinite(value):
                    del region2value[region]
                    print "REMOVED:", value, " for ", region, " ", property
            if len(region2value) == 0:
                del property2region2value[property]
                print "REMOVED property:", property, " no values left"
            else:
                valueCounter += len(region2value) 
                regions = regions.union(set(region2value.keys()))

        print len(property2region2value), " properties"
        print len(regions),  " unique regions"
        print valueCounter, " values loaded"
        return property2region2value
    
    def train(self, trainMatrix, textMatrix, params):
        pass
        
    def predict(self, property, region):
        pass
         
    @classmethod
    def runRelEval(cls, d, property, trainRegion2value, textMatrix, testRegion2value, ofn, params):        
        predictor = cls()
        of = open(ofn, "w")
        print "Training"
        
        #try:
            #cProfile.runctx('predictor.trainRelation(property, trainRegion2value, textMatrix, of, params)', globals(), locals())

        predictor.trainRelation(property, trainRegion2value, textMatrix, of, params)
        print "Done training"
        #except FloatingPointError:
        #    print "Training with params ", params, " failed due to floating point error"
        #    avgScore = float("inf")
        #else:
        print "Testing"
        predMatrix = {}
        predMatrix[property] = {}
        for region in testRegion2value:
            predMatrix[property][region] = predictor.predict(property, region, of)
            
        testMatrix = {}
        testMatrix[property] = testRegion2value
        avgScore = predictor.eval(predMatrix, testMatrix, of)
        of.write("fold MAPE:" + str(avgScore) + "\n")
        
        # Now repeat the prediction but now do not use defaults
        of.write("Evaluation without using the defaults\n")
        predMatrix = {}
        predMatrix[property] = {}
        for region in testRegion2value:
            val = predictor.predict(property, region, of, False)
            if val != None:
                predMatrix[property][region] = val
        coverage = float(len(predMatrix[property]))/len(testMatrix[property])
        if coverage > 0:
            avgScoreNoDefault = predictor.eval(predMatrix, testMatrix, of)
            of.write("fold MAPE without defaults:" + str(avgScoreNoDefault) +" coverage " + str(coverage) + "\n")
        else:
            of.write("No values predicted.\n")
        
        
        if ofn.split("_")[-1] == "TEST":
            d["TEST"] =  avgScore
        else:
            d[int(ofn.split("_")[-1])] =  avgScore
        return avgScore
            
        #finally:
        of.close()
    
    
    # the paramSets
    @classmethod
    def crossValidate(cls, trainMatrix, textMatrix, folds, properties, outputFileName, paramSets, multi=True):
        # first construct the folds per relation
        property2folds = {}
        # we set the same random in order to get the same folds every time
        # we do it on the whole dataset everytime independently of the choice of properties
        random.seed(13)
        # For each property
        for property, region2value in trainMatrix.items():
            # create the empty folds
            property2folds[property] = [{} for _ in xrange(folds)]
            # shuffle the data points
            regions = region2value.keys()
            random.shuffle(regions)
            for idx, region in enumerate(regions):
                # pick a fold
                foldNo = idx % folds
                # add the datapoint there
                property2folds[property][foldNo][region] = region2value[region]
        
        # here we keep the best params found for each relation 
        property2bestParams = {}        
        bestParams = [None]

        # for each of the properties we decide 
        for property in properties:
            print "property: " + property
            # this keeps the lowest MAPE achieved for this property across folds
            lowestAvgMAPE = float("inf")                
            
            for params in paramSets:
                print "params: ", params 
                
                if multi:
                    # this is to do the cross validation across folds
                    mgr = multiprocessing.Manager()
                    d = mgr.dict()    
                    jobs = []
                else:
                    d= {}

                
                paramMAPEs = []
                # for each fold    
                
                for foldNo in xrange(folds):
                    print "fold:", foldNo
                    # construct the training and test datasets
                    foldTrainRegion2value = {}
                    foldTestRegion2value = {}
                    data = property2folds[property]

                    foldTrainMatrix = {}
                    for idx in xrange(folds):
                        if (idx % folds) == foldNo:
                            # this the test data
                            foldTestRegion2value = data[idx]
                        else:
                            # the rest adds to the training data
                            foldTrainRegion2value.update(data[idx])
                            
                    # now create a predictor and run the eval
                    predictor = cls()
                    # run the eval
                    # open the file for the relation, fold and params
                    paramsStrs = []
                    for param in params:
                        paramsStrs.append(str(param))
                    #print outputFileName
                    #print paramsStrs
                    #print "_".join(paramsStrs)
                    #print property.split("/")[-1]
                    ofn = outputFileName + "_" + property.split("/")[-1] + "_" + "_".join(paramsStrs) + "_" + str(foldNo)
                    if multi:                    
                        job = multiprocessing.Process(target=predictor.runRelEval, args=(d, property, foldTrainRegion2value, textMatrix, foldTestRegion2value, ofn, params,))
                        jobs.append(job)
                    else:
                        predictor.runRelEval(d, property, foldTrainRegion2value, textMatrix, foldTestRegion2value, ofn, params)

                if multi:
                    # start all the jobs
                    for j in jobs:
                        j.start()

                    # Ensure all of the processes have finished
                    for j in jobs:
                        j.join()
                    
                orderedFold2MAPE = OrderedDict(sorted(d.items(), key=lambda t: t[0]))                    
                # get the average across folds    
                if float("inf") not in orderedFold2MAPE.values():
                    avgMAPE = numpy.mean(orderedFold2MAPE.values())
                    print property + ":params:", params, " avgMAPE:", avgMAPE, "stdMAPE:", numpy.std(orderedFold2MAPE.values()), "foldMAPEs:", orderedFold2MAPE.values()
                    # lower is better
                    if avgMAPE <= lowestAvgMAPE:
                        bestParams = params
                        lowestAvgMAPE = avgMAPE
                    
                else:
                    print property + ":params:", params, "Training in some folds failed due to overflow", "foldMAPEs:", orderedFold2MAPE.values()
            
                

            print property + ": lowestAvgMAPE:", lowestAvgMAPE
            print property + ": bestParams: ", bestParams
            property2bestParams[property] = bestParams
            
        # we return the best params 
        return property2bestParams
            
                
    @staticmethod
    def eval(predMatrix, testMatrix, of):
        of.write(str(predMatrix) +"\n")
        of.write(str(testMatrix) +"\n")
        property2MAPE = {}
        property2MASE = {}
        property2RMSE = {}
        for property, predRegion2value in predMatrix.items():
            of.write(property+"\n")
            #print "real: ", testMatrix[property]
            #print "predicted: ", predRegion2value
            mape = AbstractPredictor.MAPE(predRegion2value, testMatrix[property])
            of.write("MAPE: " + str(mape) + "\n")
            property2MAPE[property] = mape
            rmse = AbstractPredictor.RMSE(predRegion2value, testMatrix[property])
            of.write("RMSE: " + str(rmse) + "\n")
            property2RMSE[property] = rmse
            mase = AbstractPredictor.MASE(predRegion2value, testMatrix[property])
            #of.write("MASE: " + str(mase) + "\n")
            property2MASE[property] = mase
            
        #return numpy.mean(MAPEs)
        of.write("properties ordered by MAPE\n")
        sortedMAPEs = sorted(property2MAPE.items(), key=operator.itemgetter(1))
        for property, mape in sortedMAPEs:
            of.write(property + ":" + str(mape)+"\n") 
                           
        #of.write("properties ordered by MASE\n")
        #sortedMASEs = sorted(property2MASE.items(), key=operator.itemgetter(1))
        #for property, mase in sortedMASEs:
        #    of.write(property + ":" + str(mase)+"\n") 
        
        
        of.write("avg. MAPE: " + str(numpy.mean(property2MAPE.values())) +"\n")
        of.write("avg. RMSE: " + str(numpy.mean(property2RMSE.values())) +"\n")
        #of.write("avg. MASE: " + str(numpy.mean(property2MASE.values())) +"\n")
        # we use MASE as the main metric, which is returned to guide the hyperparamter selection
        return numpy.mean(property2MAPE.values())
    
    # We follow the definitions of Chen and Yang (2004)
    # the second dict does the scaling
    # not defined when the trueDict value is 0
    # returns the mean absolute percentage error and the number of predicted values used in it
    @staticmethod
    def MAPE(predDict, trueDict, verbose=False):        
        absPercentageErrors = {}
        keysInCommon = list(set(predDict.keys()) & set(trueDict.keys()))
                
        #print keysInCommon
        for key in keysInCommon:
            # avoid 0's
            if trueDict[key] != 0:
                absError = abs(predDict[key] - trueDict[key])
                absPercentageErrors[key] = absError/numpy.abs(trueDict[key])
        
        if len(absPercentageErrors) > 0:     
            if verbose:
                print "MAPE results"
                sortedAbsPercentageErrors = sorted(absPercentageErrors.items(), key=operator.itemgetter(1))
                print "top-5 predictions"
                print "region:pred:true"
                for idx in xrange(5):
                    print sortedAbsPercentageErrors[idx][0].encode('utf-8'), ":", predDict[sortedAbsPercentageErrors[idx][0]], ":", trueDict[sortedAbsPercentageErrors[idx][0]] 
                print "bottom-5 predictions"
                for idx in xrange(5):
                    print sortedAbsPercentageErrors[-idx-1][0].encode('utf-8'), ":", predDict[sortedAbsPercentageErrors[-idx-1][0]], ":", trueDict[sortedAbsPercentageErrors[-idx-1][0]]
            
            return numpy.mean(absPercentageErrors.values())
        else:
            return float("inf")

    
    # This is MASE, sort of proposed in Hyndman 2006
    # at the moment the evaluation metric of choice
    # it returns 1 if the method has the same absolute errors as the median of the test set.
    @staticmethod
    def MASE(predDict, trueDict, verbose=False):
        # first let's estimate the error from the median:
        median = numpy.median(trueDict.values())
        
        # calculate the errors of the test median
        # we are scaling with the error of the median on the value at question. This will be 0 often, thus we want to know the smallest non-zero to add it.
        minMedianAbsError = float("inf")
        for value in trueDict.values():
            medianAbsError = numpy.abs(value - median)
            if medianAbsError > 0 and medianAbsError < minMedianAbsError:
                minMedianAbsError = medianAbsError
        
    
        # get those that were predicted
        keysInCommon = list(set(predDict.keys()) & set(trueDict.keys()))
        predScaledAbsErrors = {}
        for key in keysInCommon:
            predScaledAbsErrors[key] = (numpy.abs(predDict[key] - trueDict[key]) + minMedianAbsError)/(numpy.abs(median - trueDict[key]) + minMedianAbsError)
        
        if verbose:
            print "MASE results"
            sortedPredScaledAbsErrors = sorted(predScaledAbsErrors.items(), key=operator.itemgetter(1))
            print "top-5 predictions"
            print "region:pred:true"
            for idx in xrange(5):
                print sortedPredScaledAbsErrors[idx][0].encode('utf-8'), ":", predDict[sortedPredScaledAbsErrors[idx][0]], ":", trueDict[sortedPredScaledAbsErrors[idx][0]] 
            print "bottom-5 predictions"
            for idx in xrange(5):
                print sortedPredScaledAbsErrors[-idx-1][0].encode('utf-8'), ":", predDict[sortedPredScaledAbsErrors[-idx-1][0]], ":", trueDict[sortedPredScaledAbsErrors[-idx-1][0]]
                
        return numpy.mean(predScaledAbsErrors.values())
                    

        

    # This is the KL-DE1 measure defined in Chen and Yang (2004)        
    @staticmethod
    def KLDE(predDict, trueDict, verbose=False):
        kldes = {}
        # first we need to get the stdev used in scaling
        # let's use all the values for this, not only the ones in common
        std = numpy.std(trueDict.values())
        keysInCommon = list(set(predDict.keys()) & set(trueDict.keys()))
        
        for key in keysInCommon:
            scaledAbsError = abs(predDict[key] - trueDict[key])/std
            klde = numpy.exp(-scaledAbsError) + scaledAbsError - 1
            kldes[key] = klde
        
        if verbose:
            print "KLDE results"
            sortedKLDEs = sorted(kldes.items(), key=operator.itemgetter(1))
            print "top-5 predictions"
            print "region:pred:true"
            for idx in xrange(5):
                print sortedKLDEs[idx][0].encode('utf-8'), ":", predDict[sortedKLDEs[idx][0]], ":", trueDict[sortedKLDEs[idx][0]] 
            print "bottom-5 predictions"
            for idx in xrange(5):
                print sortedKLDEs[-idx-1][0].encode('utf-8'), ":", predDict[sortedKLDEs[-idx-1][0]], ":", trueDict[sortedKLDEs[-idx-1][0]]
                
        return numpy.mean(kldes.values())
    
    # This does a scaling according to the number of values actually used in the calculation
    # The more values used, the lower the score (lower is better)
    # smaller scaling parameters make the number of values used more important, larger lead to the same as standard KLDE
    # Inspired by the shrunk correlation coefficient (Koren 2008 equation 2)
    @staticmethod
    def supportScaledKLDE(predDict, trueDict, scalingParam=1):
        klde = AbstractPredictor.KLDE(predDict, trueDict)
        keysInCommon = list(set(predDict.keys()) & set(trueDict.keys()))               
        scalingFactor = scalingParam/(scalingParam + len(keysInCommon))
        return klde * scalingFactor

    @staticmethod
    def supportScaledMASE(predDict, trueDict, scalingParam=1):
        mase = AbstractPredictor.MASE(predDict, trueDict)
        keysInCommon = list(set(predDict.keys()) & set(trueDict.keys()))               
        scalingFactor = float(scalingParam)/(scalingParam + len(keysInCommon))
        return mase * scalingFactor        

    @staticmethod
    def supportScaledMAPE(predDict, trueDict, scalingParam=1):
        mape = AbstractPredictor.MAPE(predDict, trueDict)
        keysInCommon = list(set(predDict.keys()) & set(trueDict.keys()))               
        scalingFactor = float(scalingParam)/(scalingParam + len(keysInCommon))
        return mape * scalingFactor        


    @staticmethod
    def RMSE(predDict, trueDict):
        keysInCommon = list(set(predDict.keys()) & set(trueDict.keys()))
        #print keysInCommon
        y_actual = []
        y_predicted = []
        for key in keysInCommon:
            y_actual.append(trueDict[key])
            y_predicted.append(predDict[key])
        return math.sqrt(mean_squared_error(y_actual, y_predicted))
        