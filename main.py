from __future__ import division
import os
import locale
import time
import datetime
import re
locale.setlocale(locale.LC_ALL, '')

# generates per-page asset reports

# ##############################################################################
# CONFIGURATION OPTIONS
fPath = 'C:/Users/user/Documents/FILELIST.txt'  # path to the master file list containing file paths from the web server root directory
localRootPath = "C:/Users/user/webserver/website"  # path to the live www root directory
remoteRootPath = "E:\\webserver\\wwwroot\\www" # path as seen in the input file (escape the \s)
outputDir = "outputByPage/"  # name of directory where reporting is saved (must exist)
pageFilter = "/" # restrict scans to URLs containing this string. use `/` to scan all
assetExtList = ['pptx','js','ppt','zip','wmv','mp3','txt','css','jpg','png','jpeg','mp4','gif','pdf','inc','doc','docx','xls','xlsx','xml','mov','dll','vb','xsl','tif','map','avi','wmv','xsd','ico','ics','bmp','wav','svg','woff','ttf','jbf'] # file extensions assets have
pageExtList = ['html','htm','asp','aspx','shtml'] # file extensions pages have
ignoredAssets = ['/favicon.ico']
urlPrefix = "https://www.website.com" # prepend this to relative paths to make a full URL
resultFile = 'assets.csv' # page report csv file
version = 0.155

htmlList = []  # page paths
assetList = []  # asset file names
assetPathsList = []  # asset full paths
discardList = []  # discarded paths
pagesNotFoundList = []  # pages not found
activeAssetSet = set()  # assets known to be employed somewhere (unique)
orphanedAssetSet = set() # assets not known to be employed anywhere
bytesRead = 0 # sum of data read in
scanRate = 0 # pages per second scanned
secsToComplete = 0 # seconds until all pages are scanned
pctComplete = format(0.0, '.1f') # percentage of pages scanned
c = 0 # loop iteration counter

def initEmptyFile(filename, title): # sets up new file
    fi = open(outputDir + filename, "w")
    fi.write("--- "+ title +" ---\n")
    fi.write("v." + str(version)+' - '+str(datetime.datetime.now())+ '\n')
    fi.close()

def writeToFile(filename, contents): # append contents to file
    fi = open(outputDir + filename, "a")
    for item in contents:
        fi.write(item + '\n')
    fi.close()

def normalizePath(pathInput):
    pathInput = pathInput.replace(remoteRootPath, localRootPath)  # make the path accessible by this computer
    pathInput = pathInput.replace("\n", "")  # clip off line break characters
    pathInput = pathInput.replace("\\", "/")  # reverse the slashes
    pathInput = pathInput.replace("//", "")  # rid double slashes
    output = pathInput.lower() # make lowercase
    return output

def printAndSave(data):
    print(data)
    fi = open(outputDir + resultFile, "a")
    fi.write(data + '\n')
    fi.close()

# ##############################################################################
# CREATE/CLEAR FILES TO BE WRITTEN
initEmptyFile("discardedInput.txt","Discarded Input")
initEmptyFile("allAssets.txt","All Assets")
initEmptyFile("activeAssets.txt","Active Assets")
initEmptyFile("pages.txt","All Pages")
initEmptyFile("pagesNotFound.txt","Pages Not Found")
initEmptyFile("orphanedAssets.txt","Orphaned Assets")
initEmptyFile(resultFile,"Assets by Page")

f = open(fPath, 'r')
linesFile = f.readlines()  # read the file list from prod file report line-wise into an array
f.close()
linesLength = len(linesFile)

# ##############################################################################
# PARSE ENTIRE FILE, SORT INTO HTML, ASSETS AND DISCARD LISTS
for path in linesFile:
    path = normalizePath(path)
    if path.count(".") > 0:  # is this even a file?
        if os.path.splitext(path)[1][1:].strip() in pageExtList and path.count(pageFilter) > 0 : # a page
            htmlList.append(path)
        elif os.path.splitext(path)[1][1:].strip() in assetExtList: # if it's one of the extensions we know of
            assetPathsList.append(path)  # add entire path to assetPathsList
            assetList.append(path.rsplit('/', 1)[-1])  # add only the filename to assetList
        else:  # unrecognized file type.
            discardList.append(path)
    else:  # there is no period in the path. directory?
        discardList.append(path)

htmlList.sort()  # alphabetize list of found pages
assetList = sorted(set(assetList))  # assetList is now sorted and unique
writeToFile("pages.txt", htmlList)
writeToFile("allAssets.txt", assetList)
writeToFile("discardedInput.txt", discardList)

# ##############################################################################
# OPEN EACH HTML FILE, PARSE CODE FOR ASSETS
startTime = time.time()
for page in htmlList:
    if os.path.exists(page):  # if it's actually there
        htmlFile = open(page, 'r')  # open it
        htmlFileCode = htmlFile.read()  # read entire file to one var
        htmlFile.close()  # close it
        htmlFileCode = htmlFileCode.lower()  # make the entire file contents lower case for good matching
        bytesRead = bytesRead + len(htmlFileCode)  # measure the length in characters

        # build list of asset hits[] based on surrounding html. which contexts to look for?
        hits = []
        for m in re.finditer('<!--#include virtual="', htmlFileCode):
            hits.append(m.start() + 22)
        for m in re.finditer('href="', htmlFileCode):
            hits.append(m.start()+6)
        for m in re.finditer('src="', htmlFileCode):
            hits.append(m.start()+5)

        hits.sort()
        printAndSave('\r')
        page = urlPrefix + page.replace(localRootPath.lower(), '')
        printAndSave(page + '\nLine#,Link')

        validHits = 0
        for hit in hits:
            hitEnd = htmlFileCode.find('"',hit,len(htmlFileCode)) # find end of link/resource destination address by finding the next double-quote
            linkAddr = htmlFileCode[hit:hitEnd] # gets link contents

            breaks = [m.start() for m in re.finditer('\n',htmlFileCode[0:hit])] # count all breaks before the search hit to derive the line #
            breaks = len(breaks) + 1 # off by one

          # IF there is anything,   AND if it has a known asset file extension,                   AND it has a period, AND it's not an email addr, AND it begins with a /,    AND it's not one of the ignored assets
            if linkAddr             and os.path.splitext(linkAddr)[1][1:].lower() in assetExtList and "." in linkAddr  and "@" not in linkAddr     and linkAddr[0] == "/"     and linkAddr not in ignoredAssets:
                # print(normalizePath(linkAddr[0]))
                if linkAddr[0] == "/" or linkAddr[0] == "/" and linkAddr[1] == "/":
                    linkAddr = normalizePath(linkAddr)
                else:
                    linkAddr = urlPrefix + normalizePath(linkAddr)
                printAndSave(str(breaks) + ',' + linkAddr) # list active asset
                validHits += 1

        if '<meta http-equiv="refresh" content="' in htmlFileCode:
            printAndSave('0,this is a redirect page')
        if validHits == 0:
            printAndSave('0,no assets used')

    else:  # if file does not exist
        pagesNotFoundList.append(page)  # add to list of unfound pages
        printAndSave('[page not found][' + page.replace(localRootPath.lower(), "") + ']')
    c += 1 # increment loop counter

writeToFile("pagesNotFound.txt", pagesNotFoundList)
writeToFile("activeAssets.txt", activeAssetSet)
