# Example/test script for using the opsimField slicer. 

import sys, os, argparse
import numpy as np
import matplotlib.pyplot as plt
import lsst.sims.maf.db as db
import lsst.sims.maf.slicers as slicers
import lsst.sims.maf.metrics as metrics
import lsst.sims.maf.sliceMetrics as sliceMetrics
import lsst.sims.maf.utils as utils

import glob

import time
def dtime(time_prev):
   return (time.time() - time_prev, time.time())


def getMetrics(docomplex=True):
    t = time.time()
    # Set up metrics.
    metricList = []
    # Simple metrics: 
    metricList.append(metrics.MeanMetric('finSeeing'))
    metricList.append(metrics.MedianMetric('airmass'))
    metricList.append(metrics.MinMetric('airmass'))
    metricList.append(metrics.MeanMetric('fiveSigmaDepth'))
    metricList.append(metrics.MeanMetric('filtSkyBrightness'))
    metricList.append(metrics.Coaddm5Metric('fiveSigmaDepth'))    
    metricList.append(metrics.CountMetric('expMJD', metricName='N_Visits',
                                          plotDict={'logScale':False, 'units':'Number of visits',
                                                      'colorMin':0, 'colorMax':300}))
    if docomplex:
        # More complex metrics.    
        dtmin = 1./60./24.
        dtmax = 360./60./24.
        metricList.append(metrics.VisitGroupsMetric(deltaTmin=dtmin, deltaTmax=dtmax))
    dt, t = dtime(t)
    print 'Set up metrics %f s' %(dt)
    return metricList
    
def getSlicer(simData, fieldData):
    # Setting up the slicer will be slightly different for each slicer.
    t = time.time()    
    bb = slicers.OpsimFieldSlicer(simDataFieldIDColName='fieldID', fieldIDColName='fieldID',
                                  fieldRaColName='fieldRA', fieldDecColName='fieldDec')
    # SetUp slicer.
    bb.setupSlicer(simData, fieldData)
    dt, t = dtime(t)
    print 'Set up slicer %f s' %(dt)
    return bb

def goSlice(opsimrun, metadata, simdata, bb, metricList):
    t = time.time()
    gm = sliceMetrics.RunSliceMetric()
    gm.setSlicer(bb)
    
    dt, t = dtime(t)
    print 'Set up gridMetric %f s' %(dt)

    gm.setMetrics(metricList)
    gm.runSlices(simdata, simDataName=opsimrun, metadata = metadata)
    dt, t = dtime(t)
    print 'Ran bins of %d points with %d metrics using sliceMetric %f s' %(len(bb), len(metricList), dt)
                    
    gm.reduceAll()
    
    dt, t = dtime(t)
    print 'Ran reduce functions %f s' %(dt)

    return gm

def plot(gm):
    t = time.time()
    gm.plotAll(savefig=True, closefig=True)
    
    dt, t = dtime(t)
    print 'Made plots %f s' %(dt)

def write(gm):
    t= time.time()
    gm.writeAll()
    dt, t = dtime(t)
    print 'Wrote outputs %f s' %(dt)

def printSummary(gm, metricList):
    t = time.time()
    for m in metricList:
       iid = gm.metricObjIid(m)[0]
       value = gm.computeSummaryStatistics(iid, metrics.MeanMetric(''))
       print 'Summary for', m.name, ':', value
    dt, t = dtime(t)
    print 'Computed summaries %f s' %(dt)


    
if __name__ == '__main__':

    # Parse command line arguments for database connection info.
    parser = argparse.ArgumentParser()
    parser.add_argument("opsimDb", type=str, help="Filename of sqlite db")
    parser.add_argument("--sqlConstraint", type=str, default="filter='r'",
                        help="SQL constraint, such as filter='r' or propID=182")
    parser.add_argument("--propID", type=int, default=-666, 
                        help="Proposal ID number if using propID as a constraint for the field data")
    args = parser.parse_args()

    # Get db connection info.
    dbAddress = 'sqlite:///' + args.opsimDb
    oo = db.OpsimDatabase(dbAddress)

    opsimrun = oo.fetchOpsimRunName()

    if args.propID == -666:
        args.propID = None
    
    sqlconstraint = args.sqlConstraint
        
    # Set up metrics. 
    metricList = getMetrics(docomplex=True)
    
    # Find columns that are required.
    colnames = list(metricList[0].colRegistry.colSet)
    colnames += ['fieldID', 'fieldRA', 'fieldDec']
    colnames = list(set(colnames))
    
    # Get opsim simulation data
    simdata = oo.fetchMetricData(colnames, sqlconstraint)

    # Set up slicer.
    fieldData = oo.fetchFieldsFromFieldTable(propID=args.propID)
    bb = getSlicer(simdata, fieldData)
    
    # Okay, go calculate the metrics.
    metadata = sqlconstraint.replace('=','').replace('filter','').replace("'",'').replace('"', '')
    gm = goSlice(opsimrun, metadata, simdata, bb, metricList)

    # Generate some summary statistics and plots.
    printSummary(gm, metricList)
    # Generate (and save) plots.
    plot(gm)

    # Write the data to file.
    write(gm)
    
