import bananopy.banano as ban
from datetime import datetime
import csv
import time
from concurrent.futures import as_completed
from requests_futures.sessions import FuturesSession
from urllib.request import urlopen
from bs4 import BeautifulSoup



# Querying the Network
numberToGet = 10000
iterator = 0
currentDate = datetime.utcnow()
if currentDate.hour >= 12:
    hour = 12
else:
    hour = 0

dateOfFold = datetime(currentDate.year, currentDate.month, currentDate.day, hour)
timeShift =  time.mktime(datetime.now().timetuple()) - time.mktime(datetime.utcnow().timetuple()) #manually implement timezone shift since mktime only accepts local time
dateOfFoldUnix = time.mktime(dateOfFold.timetuple()) + timeShift
print("Querying for Payout on", dateOfFold.strftime("%d-%b-%Y %H UTC"))
account = "ban_3fo1d1ng6mfqumfoojqby13nahaugqbe5n6n3trof4q8kg5amo9mribg4muo"

tempjson = ban.account_history(account, numberToGet)    
while True:
    print(numberToGet, dateOfFoldUnix, tempjson['history'][-1]['local_timestamp'] )
    transactionCount = 0
    listOfFolders = []
    for transaction in tempjson['history']:
        if transaction['local_timestamp'] > dateOfFoldUnix and transaction['type'] == 'send' : #adding logic to ignore future folds here
            listOfFolders.append(transaction['account'])
            transactionCount += 1
    if tempjson['history'][-1]['local_timestamp']  < dateOfFoldUnix:
        break
    else:
        tempjson = ban.account_history(account, numberToGet, head=tempjson['previous'])

print("Total Sends: ", transactionCount)

currentDate = datetime.utcnow()
if currentDate.hour >= 12:
    hour = 12
else:
    hour = 0
dateOfFold = datetime(currentDate.year, currentDate.month, currentDate.day, hour)




chunkSize = 10
chunks = [listOfFolders[x:x+chunkSize] for x in range(0, len(listOfFolders), chunkSize)]
masterList = []
scrapeStartTime = time.time()
timeList = [scrapeStartTime, scrapeStartTime, scrapeStartTime, scrapeStartTime, scrapeStartTime, scrapeStartTime, scrapeStartTime, scrapeStartTime, scrapeStartTime, scrapeStartTime]
scrapeErrorCount = 0
masterList.append(['username','payout','points','total_payout','total_points','total_wus','created_at'])

headers = {"User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 12871.102.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.141 Safari/537.36"}
print(str(len(chunks)) + " chunks generated")
print("Outputting to: " + 'scrape_latest.csv')
i = 1

BANsum = 0
for chunk in chunks:
    with FuturesSession() as session:
        futures = [session.get('https://bananominer.com/user_address/' + userName, headers=headers, timeout=20) for userName in chunk]
        for future in as_completed(futures):
            try:
                response = future.result()
                user = response.json()
                dateString = user['payments'][0]['created_at'][:-1]
                while len(dateString) < 26:
                    dateString += "0"
                payoutTime = datetime.fromisoformat(dateString)
                if payoutTime > dateOfFold: #I think this is where I would change it
                    total_payout = 0
                    for payout in user['payments']:
                        total_payout += payout['amount']
                    masterList.append([user['user']['id'],
                                      user['payments'][0]['amount'],
                                       user['payments'][0]['score'] - user['payments'][1]['score'],
                                       round(total_payout, 2),
                                       user['payments'][0]['score'],
                                       user['payments'][0]['work_units'],
									   user['user']['created_at']
                                       ])
                    print(user['user']['id'] + ": Folded " + str(user['payments'][0]['score'] - user['payments'][1]['score']) +" points for " + str(user['payments'][0]['amount']) + " BAN")
                    BANsum += user['payments'][0]['amount']
                else:
                    print(user['user']['id'] + ": No payment found")
            except IndexError:
                pass
            except Exception as e:
                print(response, e)
                scrapeErrorCount += 1
    print("Finished Chunk " + str(i) + " of " + str(len(chunks)) + ". Payouts Found: " + str(len(masterList)) + ". BAN Distributed: " + str(round(BANsum, 2)))
    scrapeDuration = time.time() - timeList[i % 10]
    timeList[i % 10] = time.time()
    estimatedTimeRemaining = (scrapeDuration / 10) * (len(chunks) - i)
    totalDuration = time.time() - scrapeStartTime
    print("Time Elapsed: " + str(int(totalDuration // 60)) + "m" + str(int(totalDuration % 60)) + "s. Estimated Time Remaining: " + str(int(estimatedTimeRemaining // 60)) + "m" + str(int(estimatedTimeRemaining % 60)) + "s.")
    print("Scraping Errors So Far: " + str(scrapeErrorCount))
    i += 1
    time.sleep(0.3)
try:
    scrapeDuration = time.time() - scrapeStartTime
    print("Total Scrape Time: " + str(int(scrapeDuration//60)) + "m" + str(int(scrapeDuration % 60)) + "s")
except Exception as e:
    print(e)
    pass

print("Outputting totals to file totals.csv" )
toAdd = [str(dateOfFold.strftime("%d-%b-%Y %H UTC")), round(BANsum, 2),len(masterList)-1]
with open('totals.csv', "r") as infile:
    reader = list(csv.reader(infile))
    reader.insert(1, toAdd)
    
with open('totals.csv', "w") as outfile:
    writer = csv.writer(outfile)
    for line in reader:
        writer.writerow(line)
    infile.close()
    outfile.close()

if len(masterList)>1:
  print("Outputting folders to file latest.csv")
  with open('latest.csv', 'w', newline='') as myFile:
      writer = csv.writer(myFile)
      for entry in masterList:
          writer.writerow(entry)
      myFile.close()
else:
  print("No Payout")
