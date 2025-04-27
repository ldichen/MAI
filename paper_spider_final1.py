import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'..'))
import utils.utils as utils

import math
import json
import requests
import datetime
import time
from dateutil import parser

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer,encoding='utf8') # Change default encoding to utf8 

import requests.packages.urllib3.util.ssl_
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL'

#pymongo版本需要低
ip = "172.21.213.33"
port = 27017
dbName = "ModelDB"
# ip = "127.0.0.1"
# port = 27017
# dbName = "ModelDB"

modelCol = utils.mongoConnect4(ip,port,dbName,"modelTemp")
paperCol = utils.mongoConnect4(ip,port,dbName,"Paper")
paperCiteCol = utils.mongoConnect4(ip,port,dbName,"PaperCite")

testCol = utils.mongoConnect4(ip,port,dbName,"test")

dates=[1000,2022]

pageSize = 25

scopusUrl = "https://api.elsevier.com/content/search/scopus"
sciUrl = "https://api.elsevier.com/content/search/sciencedirect"

api_key_num = 0

scopusSearch_starttime = datetime.datetime.now()
def getResponse(uri,params):
    find = False
    while find == False:
        try:
            global scopusSearch_starttime
            endtime = datetime.datetime.now()
            duringtime = endtime - scopusSearch_starttime
            timeRange = duringtime.microseconds/1000000
            if timeRange<0.15:# scopus abstract 每周10000配额，9次/s，scopus search 每周20000配额，9次/s
                time.sleep(0.15-timeRange)    

            response = requests.get(uri,params=params,headers=utils.getHeaders(),timeout=10)

            scopusSearch_starttime = datetime.datetime.now()
            # 是否超额
            if not response.ok:
                print(response.reason)
                sys.stdout.flush()
                if response.reason == "Not Found":
                    return None
                else:
                    global api_key_num
                    api_key_num += 1
                    if api_key_num == len(open("scopus/apiKey_cry.txt",'r').readlines()):
                        api_key_num = 0
                    params["apiKey"] = utils.getLineInFile(api_key_num,"scopus/apiKey_cry.txt")

            else: 
                find = True
                return response
                             
        except Exception as e:
            print(e)
            print(uri+" reload")
            sys.stdout.flush()

sciSearch_starttime = datetime.datetime.now()
def putResponse(uri,params,headers):
    find = False
    while find == False:
        try:
            global sciSearch_starttime
            endtime = datetime.datetime.now()
            duringtime = endtime - sciSearch_starttime
            timeRange = duringtime.microseconds/1000000
            if timeRange<0.6: # sciencceDirect search 每周20000配额，2次/s
                time.sleep(0.6-timeRange)            

            response = requests.put(uri,data=json.dumps(params),headers=headers,timeout=10)
            sciSearch_starttime = datetime.datetime.now()
            # 如果超额
            if not response.ok:
                print(response.reason)
                sys.stdout.flush()
                global api_key_num
                api_key_num += 1
                if api_key_num == len(open("scopus/apiKey_cry.txt",'r').readlines()):
                    api_key_num = 0
                headers["x-els-apikey"] = utils.getLineInFile(api_key_num,"scopus/apiKey_cry.txt")

            else: # 不超额
                find = True
                return response
                
        except:
            print(uri+" reload")
            sys.stdout.flush()

def scopusSearch(queryStr,start,pageSize):
    params = {
        "start":start,
        "count":pageSize,
        "query":queryStr,
        "apiKey":utils.getLineInFile(api_key_num,"scopus/apiKey_cry.txt"),
    }

    response = getResponse(scopusUrl, params)

    pageJson = json.loads(response.text.replace('$','value').replace("prism:","").replace("dc:","").replace("dcterms:","").replace('&nbsp;', ' ').replace(u'\xa0', u' ').replace(u'\xae', u' '))
    print("scopusSearch " + queryStr + " is finished!")
    sys.stdout.flush()
    return pageJson

def sciSearch(queryStr,dateFrom,dateEnd,offset,pageSize):
    params = {
        "qs": queryStr,
        "date":str(dateFrom)+"-"+str(dateEnd),
        "display": {
            "offset": offset,
            "show": pageSize,
            "sortBy": "date"
        }
    }
    headers = {'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-els-apikey': utils.getLineInFile(api_key_num,"scopus/apiKey_cry.txt"),
        'User-Agent': utils.getUserAgent()}

    
    response = putResponse(sciUrl,params,headers)
    responseBody = json.loads(response.text.replace('&nbsp;', ' ').replace(u'\xa0', u' '))
    print("sciSearch " + queryStr + " is finished!")
    sys.stdout.flush()
    return responseBody

def citeSearch(queryStr):
    print(queryStr)
    result = []
    citedByStart = 0
    citedByTotal = 1
    citedByNum = 0
    while citedByStart < citedByTotal:

        citedByPageJson = scopusSearch(queryStr,citedByStart,pageSize)
        citedBySearchResults = citedByPageJson["search-results"]
        citedByTotal = int(citedBySearchResults["opensearch:totalResults"])
        citedByEntryList = citedBySearchResults["entry"]
        
        if len(citedByEntryList) == 1 and utils.keyInJson("error",citedByEntryList[0]):
            return result

        for entry in citedByEntryList:

            entry = changeField(entry,"scopus")

            result.append(entry)
            citedByNum += 1
            print(str(citedByNum)+"/"+str(citedByTotal) )
            sys.stdout.flush()

        citedByStart += pageSize
        print("cite " + queryStr + " is finished!")
    return result

def search(startYearIndex, endCount, model, full, abbrev, searchType, source):
    print(searchType+"-"+source+"-"+model["full"]+"-"+model["abbrev"])
    paperList = [] if not utils.keyInJson("paperList",model) else model["paperList"]
    #for d in range(startYearIndex,len(dates)-1):
    d = startYearIndex
    global dates
    while d < len(dates)-1:
        count = endCount
        endCount = 0
        start = math.floor((count)/pageSize)*pageSize                
        total = start+1                
        startYear = dates[d]
        endYear = dates[d+1]

        if source == 'scopus':
            if searchType == 'f':
                queryStr = 'TITLE-ABS-KEY ( "'+full+'" ) ' 
            else:
                queryStr = 'TITLE-ABS-KEY ( '+abbrev+' AND model ) ' 
            queryStr += ' AND  PUBYEAR  >  ' + str(startYear) + '  AND  PUBYEAR  <  ' + str(endYear+1)

            pageJson = scopusSearch(queryStr,start,pageSize)

            searchResults = pageJson["search-results"]
            total = int(searchResults["opensearch:totalResults"])
            if total == 0:
                d += 1
                continue
            entryList = searchResults["entry"]
        else:
            if searchType == "f":
                queryStr = "\""+full+"\""
            else:
                queryStr = abbrev + " AND model"

            pageJson = sciSearch(queryStr,startYear+1,endYear,start,pageSize)
            sys.stdout.flush()
            total = pageJson["resultsFound"]     
            if total == 0:
                d += 1
                continue
            entryList = pageJson["results"]


        # if total > 5000:
        #     if len(dates) == 2:
        #         dates.insert(1,1970)
        #     else:
        #         try:
        #             midYear = utils.getMidYear(dates[d],dates[d+1])
        #             if midYear == 0:
        #                 total = 5000
        #                 break
        #             dates.insert(d+1, midYear)
        #         except:
        #             break
        #     continue
        if total > 5000:
            try:
                midYear = utils.getMidYear(dates[d],dates[d+1])
                if midYear == 0:
                    total = 5000
                    break
                dates.insert(d+1, midYear)
            except:
                break
            continue

        while start < total:
            print(str(startYear)+"-"+str(endYear))
            sys.stdout.flush()
            if source == 'scopus':
                if searchType == 'f':
                    queryStr = 'TITLE-ABS-KEY ( "'+full+'" ) ' 
                else:
                    queryStr = 'TITLE-ABS-KEY ( '+abbrev+' AND model ) ' 
                queryStr += ' AND  PUBYEAR  >  ' + str(startYear) + '  AND  PUBYEAR  <  ' + str(endYear+1)

                pageJson = scopusSearch(queryStr,start,pageSize)

                searchResults = pageJson["search-results"]
                # total = int(searchResults["opensearch:totalResults"])
                entryList = searchResults["entry"]
            else:
                if searchType == "f":
                    queryStr = "\""+full+"\""
                else:
                    queryStr = abbrev + " AND model"

                pageJson = sciSearch(queryStr,startYear+1,endYear,start,pageSize)
                # total = pageJson["resultsFound"]
                if total == 0:
                    continue
                entryList = pageJson["results"]

            for e in range(count%pageSize,len(entryList)):
                entry = entryList[e]
                canpass = False
                if not utils.keyInJson("error",entry):
                    canpass = True

                if canpass: 
                    canpass = False
                    entry = changeField(entry,source)

                    ras = entry["researchArea"] if utils.keyInJson("researchArea",entry) else []
                    for area in ras:
                        if area["abbrev"] == "ENVI" or area["abbrev"] == "AGRI" or area["abbrev"] == "EART" or area["abbrev"] == "DECI":
                            canpass = True
                            break
                if canpass:                          
                    # 若为简称搜索，则需判断参考文献是否含全称      
                    relate = False             
                    if searchType == "a":
                        if not utils.keyInJson("eid",entry):
                            pass
                        else:                          
                            citedIds = entry["eid"].split("-")
                            queryStr = "CITEID(" + citedIds[len(citedIds)-1] + ") AND TITLE-ABS-KEY(\""+full+"\")"
                            refPageJson = scopusSearch(queryStr,0,10)
                            refSearchResults = refPageJson["search-results"]
                            refTotal = int(refSearchResults["opensearch:totalResults"])
                            if refTotal>0:
                                relate = True
                    elif searchType == "f":
                        relate = True
                    

                    if relate:
                        # 判断数据库中是否已经存在该文献
                        dupResult = utils.getDuplication(paperCol,entry)
                        if dupResult != None: # 存在
                            # 去重
                            paperListFind = False
                            for p in paperList:
                                if p == dupResult:
                                    paperListFind = True
                                    break
                            if not paperListFind:
                                paperList.append(dupResult)
                        else:
                            # 施引文献
                            if not utils.keyInJson("eid",entry):
                                pass
                            else:
                                citedByCount = int(entry["citedby-count"])
                                if citedByCount > 0:
                                    queryStr = "REF( " + entry["eid"] + " )"
                                    citedByItems = citeSearch(queryStr)
                                    # entry["citedByItems"] = citedByItems
                                    citings = []
                                    for cite in citedByItems:
                                        # 去重
                                        dupResult = utils.getDuplication(paperCiteCol,cite)
                                        if dupResult == None:
                                            inResult = paperCiteCol.insert_one(cite)
                                            citings.append(inResult.inserted_id)
                                        else:
                                            citings.append(dupResult)
                                    entry["citings"] = citings
                            inResult = paperCol.insert_one(entry)
                            paperList.append(inResult.inserted_id)
                        # 更新
                        model["paperList"] = paperList
                        modelCol.update_one({"_id":model["_id"]},{'$set':{"paperList":paperList}}) 
                
                count += 1
                with open("configure/paperSearch1.conf","w") as f:
                    f.write(str(model["_id"])+"\n")
                    f.write(str(startYear)+"\n")
                    f.write(str(endYear)+"\n")
                    f.write(str(count)+"\n")
                    f.write(searchType+"\n")
                    f.write(source+"\n")
                print(source+" "+searchType+" "+str(startYear) + " " + str(count) + "/" + str(total) + " " + entry["title"] if utils.keyInJson("title",entry) else "")
                sys.stdout.flush()
                
            start += pageSize   
        d += 1
    with open("configure/paperSearch1.conf","w") as f:
        f.write(str(model["_id"])+"\n")
        f.write("finish\n")
        f.write("finish\n")
        f.write("finish\n")
        f.write(searchType+"\n")
        f.write(source+"\n")

    if not utils.keyInJson("paperList",model):
        return 0
    else:
        return len(model["paperList"])

def changeField(entry,source):
    # 请求作者、机构、摘要信息
    if source == "scopus":
        fieldUrl = "https://api.elsevier.com/content/abstract/eid/"+entry["eid"]
    else:
        fieldUrl = "https://api.elsevier.com/content/abstract/pii/"+entry["pii"]
    
    fieldParams = {
        "field":"author,affiliation,description,authkeywords,subject-area,eid,citedby-count",
        "apiKey":utils.getLineInFile(api_key_num,"scopus/apiKey_cry.txt")
    }

    fieldResponse = getResponse(fieldUrl, fieldParams)

    if fieldResponse != None:

        responseJson = json.loads(fieldResponse.text.replace("$","value").replace("dc:","").replace("ce:","").replace("@","").replace('&nbsp;', ' ').replace(u'\xa0', u' '))
        if utils.keyInJson("service-error",responseJson):
            entry["error"] = responseJson["service-error"]["status"]
            return entry

        fieldInfo = responseJson["abstracts-retrieval-response"]
        
        
        abstract = None
        agencies = []
        authors = []
        authorKeywords = []
        researchAreas = []
        
        # 摘要
        if utils.keyInJson("coredata",fieldInfo):
            if utils.keyInJson("description",fieldInfo["coredata"]):
                abstract = fieldInfo["coredata"]["description"]
        
        # 机构
        if utils.keyInJson("affiliation",fieldInfo):
            affiliationJson = fieldInfo["affiliation"]
            if utils.keyInJson("affilname",affiliationJson):
                if utils.keyInJson("id",affiliationJson):
                    affilId = affiliationJson["id"]
                else :
                    affilId = None 
                agency = {
                    "id":affilId,
                    "orgName":affiliationJson["affilname"]
                }
                agencies.append(agency)
            else :
                for affil in affiliationJson:
                    if utils.keyInJson("id",affil):
                        affilId = affil["id"]
                    else :
                        affilId = None 
                    agency = {
                        "id":affilId,
                        "orgName":affil["affilname"]
                    }
                    agencies.append(agency)

        # 作者
        if utils.keyInJson("authors",fieldInfo):
            authorsJson = fieldInfo["authors"]
            if utils.keyInJson("surname",authorsJson):
                affilId = authorsJson["affilation"]["id"]
                aff = None
                for agency in agencies:
                    if agency["id"] == affilId:
                        aff = agency
                        break
                author = {
                    "name":authorsJson["surname"]+" "+authorsJson["given-name"],
                    "org":[aff]
                }
                authors.append(author)

        # 关键字
        if utils.keyInJson("authkeywords",fieldInfo):
            if utils.keyInJson("author-keyword",fieldInfo["authkeywords"]):
                keywordJson = fieldInfo["authkeywords"]["author-keyword"]       
                if utils.keyInJson("value",keywordJson):
                    authorKeywords.append(keywordJson["value"])
                else:
                    for keyword in keywordJson:
                        authorKeywords.append(keyword["value"])

        # 学科领域
        if utils.keyInJson("subject-areas",fieldInfo):
            if utils.keyInJson("subject-area",fieldInfo["subject-areas"]):
                subjectAreaJson = fieldInfo["subject-areas"]["subject-area"]       
                if utils.keyInJson("abbrev",subjectAreaJson):
                    researchAreas.append(subjectAreaJson)
                else:
                    researchAreas = subjectAreaJson
        # eid
        if not utils.keyInJson("eid",entry):
            if utils.keyInJson("coredata",fieldInfo):
                if utils.keyInJson("eid",fieldInfo["coredata"]):
                    entry["eid"] = fieldInfo["coredata"]["eid"]
                    entry["citedby-count"] = fieldInfo["coredata"]["citedby-count"]

        entry["abstract"] = abstract
        entry["author"] = authors
        entry["agency"] = agencies
        entry["authorKeyword"] = authorKeywords
        entry["researchArea"] = researchAreas

    # 字段名调整  
    if source == "scopus":
        entry["issue"] = entry["issueIdentifier"] if utils.keyInJson("issueIdentifier",entry) else None
        entry["pages"] = entry["pageRange"] if utils.keyInJson("pageRange",entry) else None
        entry["published"] = parser.parse(entry["coverDate"].replace("-00","-01")) if utils.keyInJson("coverDate",entry) else None
        entry["publishedStr"] = entry["coverDate"] if utils.keyInJson("coverDate",entry) else None
        entry["source"] = "scopus"
    else:
        if utils.keyInJson("volumeIssue",entry):
            volumeIssueArr = entry["volumeIssue"].split(", ")
            for it in volumeIssueArr:
                if it.lower().find("volume") != -1:
                    entry["volumn"] = it.split(" ")[1]
                if it.lower().find("issue") != -1:
                    entry["issue"] = it.split(" ")[1]
        if utils.keyInJson("pages",entry):
            pages = entry["pages"]
            entry["pages"] = ""
            if utils.keyInJson("first",pages):
                entry["pages"] = pages["first"]
                if utils.keyInJson("last",pages):
                    entry["pages"] += ("-"+pages["last"])

        entry["published"] = parser.parse(entry["publicationDate"]) if utils.keyInJson("publicationDate",entry) else None
        entry["publishedStr"] = entry["publicationDate"] if utils.keyInJson("publicationDate",entry) else None
        entry["publicationName"] = entry["sourceTitle"]
        entry["source"] = "sciDir"

    return entry

def run():
    startYearIndex = 0
    nextModel = True
    for model in modelCol.find().sort("_id",1):
        abbrev = model["abbrev"]
        full = model["full"]

        finish = False
        if nextModel == False:
            startYear = 1000
            startYearIndex = 0
            endCount = 0
            searchType = "f"
            source = "scopus"
        else:
        # 寻找起始模型
            try:
                with open("configure/paperSearch1.conf","r") as f:
                    modelId = f.readline().replace("\n","").strip() # 模型id
                    startYear = f.readline().replace("\n","") # 搜索起始年份
                    endYear = f.readline().replace("\n","") # 搜索终止年份
                    endCount = f.readline().replace("\n","") # 在本次搜索结果中遍历到了第几个
                    searchType = f.readline().replace("\n","") # 搜索模式 f:全称 a:简称
                    source = f.readline().replace("\n","") # 数据源 scopus sciDir

                if startYear == "finish": #单类型搜索完毕，搜索下一类型
                    finish = True
                    startYear = 1000
                    startYearIndex = 0
                    endCount = 0
                else :
                    startYear = int(startYear)
                    endYear = int(endYear)
                    endCount = int(endCount)

                    global dates
                    for d in range(0,len(dates)-1):
                        if dates[d] == startYear:
                            startYearIndex = d
                        
                            if dates[d+1] == endYear:                           
                                break
                            else:
                                dates.insert(d+1, endYear)
                                break
                        else:
                            year1 = int(dates[d])
                            year2 = int(dates[d+1])
                            yearStart = int(startYear)
                            if yearStart > year1 and yearStart < year2:
                                dates.insert(d+1, startYear)
                                startYearIndex = d+1
                                if dates[d+2] == endYear:
                                    break
                                else:
                                    dates.insert(d+2, endYear)      
                                    break                

                if nextModel == True and (modelId == '' or modelId == str(model["_id"])):
                    nextModel = False
            except:
                nextModel = False
                startYear = 1000
                startYearIndex = 0
                endCount = 0
                searchType = "f"
                source = "scopus"

            if nextModel:
                continue

        print(model["abbrev"] + " " + model["full"])
        sys.stdout.flush()

        paperNum = 0
        if utils.keyInJson("paperList",model):
            paperNum = len(model["paperList"])

        # search
        if abbrev != "" and full != "":

            # 找到模型后，开始继续抓取数据
            if not finish:
                paperNum = search(startYearIndex,endCount,model,full,abbrev,searchType,source)
            while True: 
                dates=[1000,2022]
                startYearIndex = 0
                endCount = 0
                if source == "scopus":
                    source = "sciDir"
                elif source == "sciDir":
                    if searchType == "f":
                        if paperNum == 0:
                            break
                        else:
                            searchType = "a"
                            source = "scopus"
                    elif searchType == "a":
                        break
                paperNum = search(startYearIndex,endCount,model,full,abbrev,searchType,source)                 
            # # 先抓取与full匹配的数据，入库
            # search(startYearIndex,endCount,model,full,abbrev,"f","scopus")
            # search(startYearIndex,endCount,model,full,abbrev,"f","sciDir")
            # # 在抓取与abbrev匹配的数据，判断是否相关，去重，入库
            # search(startYearIndex,endCount,model,full,abbrev,"a","scopus")
            # search(startYearIndex,endCount,model,full,abbrev,"a","sciDir")

        # 仅有全称
        elif full != "":
            if not finish:
                search(startYearIndex,endCount,model,full,abbrev,"f",source)
            while True:
                startYearIndex = 0
                endCount = 0
                if source == "scopus":
                    source = "sciDir"
                else:
                    break
                search(startYearIndex,endCount,model,full,abbrev,"f",source)

        # 仅有简称
        elif abbrev != "":
            if not finish:
                search(startYearIndex,endCount,model,full,abbrev,"a",source)
            while True:
                startYearIndex = 0
                endCount = 0
                if source == "scopus":
                    source = "sciDir"
                else:
                    break
                search(startYearIndex,endCount,model,full,abbrev,"a",source)
            


if __name__ == "__main__":
    run()