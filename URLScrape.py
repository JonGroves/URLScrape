#--- Imports ---#
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
import pandas as pd
import random
import time
from os import path
from urllib.parse import urlsplit, parse_qs, urlencode, urlparse #for cleaning up urls
from shutil import copy #for journaling the exported file
from os import remove #for journaling the exported file
import re #Regex
#--- End of Imports ---#

#--- Parameters ---#
#Get HTML
projectName = ''
mainUrl = '' #e.g. https://www.url.com
query = '' #Search query for use in startUrl
city = '' #Search city for use in startUrl
province = '' #Search province for use in startUrl
radius = '' #Search radius for use in startUrl
startUrl = '' #e.g. f'https://www.url.com/search?q={query}&l={city},+{province}&radius={radius}&sort=date'
sectionDivider = '' #HTML "class" that divides the results into individual results
#--- End of Parameters ---#

#--- Options ---#
getFullDescriptionOption = True
#--- End of Options ---#

#--- Globals ---#
newResults=[]
today = date.today()
#--- End of Globals ---#

#--- Functions ---#
#Converts "x days old" to a date that the item was posted
def convertDaysOldToPostedDate(resultDate):
    if resultDate == 'Today':
        return today
    elif resultDate == '30+ days ago':
        return 'Unknown'
    elif resultDate.find(' ago'):
        return today - timedelta(int(resultDate.replace('day ago','').replace('days ago','')))
    else:
        return False

#Return the HTML tag if it exists, else return a blank tag
def returnTag(tag):
    return tag if tag else BeautifulSoup('') #Return an empty tag if item doesn't exist so parsing doesn't produce errors
#--- End of Functions ---#

response = requests.get(startUrl) #Get webpage
soup = BeautifulSoup(response.text) #Parse HTML

items = soup.findAll("div", class_=sectionDivider)
for i, item in enumerate(items):
    print(f"Parsing {i+1} of {len(items)}")
    result={} #Set up empty dict
    #Add data to dictionary
    result['Id'] = item['id'].replace('pj_','').replace('p_','')
    result['DatePosted'] = convertDaysOldToPostedDate(returnTag(item.find('span', class_ = 'date')).text)
    result['Title'] = returnTag(item.find('h2', class_ = 'title')).text.strip().replace('\nnew','') 
    result['Location'] = returnTag(item.find('span', class_ = 'location')).text.strip().replace('\nnew','')
    if result['Location'] == '':
        result['Location'] = returnTag(item.find('div', class_ = 'location')).text.strip().replace('\nnew','')
    result['Summary'] = returnTag(item.find('div', class_ = 'summary')).text.strip()
    result['Url'] = f'{mainUrl}?' + urlencode({'jk': result['Id']})
    #Get full description, if requested
    uncleanedUrl = returnTag(item.find('a', class_ = re.compile('.*title')))['href'] # The full url, with any extra parameters still appended
    if (getFullDescriptionOption and uncleanedUrl != ''):
        print(" Getting full description...", end = '') 
        descriptionResponse = requests.get(mainUrl + uncleanedUrl)
        descriptionSoup = BeautifulSoup(descriptionResponse.text)
        result['FullDescription'] = returnTag(descriptionSoup.find('div', attrs = {'id': re.compile('.*DescriptionText')})).text
        sleepTime = 0.5 + random.random() * 10
        print("Done. Sleeping for  %.2f" % sleepTime,' seconds...', end='')
        time.sleep(0.5 + random.random() * 10)
        print("Done.")
    newResults.append(result) #Append this result to the master list of all results
    
#Convert to DataFrame
filePath = f"{city}_{query}_{projectName}_Results.csv"
newResultsDF = pd.DataFrame(newResults, dtype=str) #Create dataFrame from new results

#Get previous data if it exists (.csv)
previousResultsDF = None
if path.isfile(filePath):
    with open(filePath) as inputFile:
        previousResultsDF = pd.read_csv(filePath, dtype=str).fillna('')

#Write new data to tmp file (.csv)
with open(filePath + '.tmp','w') as outputFile:
    if isinstance(previousResultsDF, pd.DataFrame): #Previous data exists:
        fullResultsDF = pd.concat([previousResultsDF, newResultsDF]).drop_duplicates(ignore_index=True) #Concatenate previous data with new data, and remove duplicates
        fullResultsDF.to_csv(outputFile, index=False) # Write to tmp file
    else: #No previous data:
        newResultsDF.to_csv(outputFile, index=False) # Write to tmp file

#Journaling of exported file (.csv)
copy(filePath + '.tmp',filePath) #Overwrite main file (to prevent losing the file if there is an IO issue
remove(filePath + '.tmp') #Delete temporary file

print("Done!")
newResultsDF #Show DataFrame
