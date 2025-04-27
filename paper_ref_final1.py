import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))
import utils.utils as utils
import json
import requests
import datetime
import time
from dateutil import parser
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')  # Change default encoding to utf8
# import requests.packages.urllib3.util.ssl_
import urllib3.util.ssl_
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL'
urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL'
from bson.objectid import ObjectId

# 设置数据库
ip = "172.21.213.33"
port = 27017
dbName = "ModelDB"
# dbName = "ModelDB2"
modelCol = utils.mongoConnect4(ip, port, dbName, "modelTemp")
paperCol = utils.mongoConnect4(ip, port, dbName, "Paper")
paperCiteCol = utils.mongoConnect4(ip, port, dbName, "PaperCite")
# 数据爬取页数
pageSize = 25
# 爬取论文网站
scopusUrl = "https://api.elsevier.com/content/search/scopus"
sciUrl = "https://api.elsevier.com/content/search/sciencedirect"
api_key_num = 0
scopusSearch_starttime = datetime.datetime.now()

def getResponse(uri, params):
    find = False
    while find == False:
        try:
            global scopusSearch_starttime
            endtime = datetime.datetime.now()
            duringtime = endtime - scopusSearch_starttime
            timeRange = duringtime.microseconds / 1000000
            if timeRange < 0.15:  # scopus abstract 每周10000配额，9次/s，scopus search 每周20000配额，9次/s
                time.sleep(0.15 - timeRange)

            response = requests.get(uri, params=params, headers=utils.getHeaders(), timeout=10)

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
                    if api_key_num == len(open("scopus/apiKey_cry.txt", 'r').readlines()):
                        api_key_num = 0
                    params["apiKey"] = utils.getLineInFile(api_key_num, "scopus/apiKey_cry.txt")

            else:
                find = True
                return response

        except Exception as e:
            print(e)
            print(uri + " reload")
            sys.stdout.flush()

def scopusSearch(queryStr,start,pageSize):
    params = {
        "start":start,
        "count":pageSize,
        "query":queryStr,
        "apiKey":utils.getLineInFile(api_key_num, "scopus/apiKey_cry.txt"),
    }

    response = getResponse(scopusUrl, params)

    pageJson = json.loads(response.text.replace('$','value').replace("prism:","").replace("dc:","").replace("dcterms:","").replace('&nbsp;', ' ').replace(u'\xa0', u' ').replace(u'\xae', u' '))
    print("scopusSearch " + queryStr + " is finished!")
    sys.stdout.flush()
    return pageJson

def citeSearch(queryStr):
    print(queryStr)
    result = []
    citedByStart = 0
    citedByTotal = 1
    citedByNum = 0
    while citedByStart < citedByTotal:

        citedByPageJson = scopusSearch(queryStr, citedByStart, pageSize)
        citedBySearchResults = citedByPageJson["search-results"]
        citedByTotal = int(citedBySearchResults["opensearch:totalResults"])
        citedByEntryList = citedBySearchResults["entry"]

        if len(citedByEntryList) == 1 and utils.keyInJson("error", citedByEntryList[0]):
            return result

        for entry in citedByEntryList:
            # entry = changeField(entry, "scopus")

            # eid = entry["eid"]
            # # 搜索已有论文是否有重复的
            # citings = paper["citings"]
            # flag = False
            # for citing in citings:
            #     query = {"_id": citing}
            #     citingPaper = utils.getQueryResultDoc(paperCol, query)
            #     if (citingPaper["eid"] == eid):
            #         flag = True
            #         break
            # if (flag == True):

            result.append(entry)
            citedByNum += 1
            print(str(citedByNum) + "/" + str(citedByTotal))
            sys.stdout.flush()

        citedByStart += pageSize
        print("cite " + queryStr + " is finished!")
    return result

def citeSearchNum(queryStr):
    # 查看当前引用数量
    print(queryStr)
    sys.stdout.flush()
    citedByStart = 0
    citedByTotal = 1
    citedByNum = 0
    while citedByStart < citedByTotal:

        citedByPageJson = scopusSearch(queryStr, citedByStart, pageSize)
        citedBySearchResults = citedByPageJson["search-results"]
        citedByTotal = int(citedBySearchResults["opensearch:totalResults"])
        citedByEntryList = citedBySearchResults["entry"]

        if len(citedByEntryList) == 1 and utils.keyInJson("error", citedByEntryList[0]):
            citedByNum += 1
            return citedByNum

        citedByNum += len(citedByEntryList)
        citedByStart += pageSize
        print("cite " + queryStr + " is finished!")

    return citedByNum

# 主程序
def run():
    for model in modelCol.find().sort("_id",1):
        modelId = model["_id"]
        # 读取当前配置文件（读到哪篇文章了）
        try:
            with open("configure/paperRef1.conf", "r") as f:
                current_model_id = f.readline().replace("\n", "").strip()  # 模型id
                current_paper_id = f.readline().replace("\n", "").strip()  # 论文id
                # 若已读取过该模型，则跳过
                if (modelId < ObjectId(current_model_id)):
                    continue
        except:
            print("no config file yet")
            current_paper_id = ""
            sys.stdout.flush()

        # 获取文章列表
        try:
            paperList = model["paperList"]
        except:
            continue
        paperList = [str(Item) for Item in paperList]
        paperList.sort()
        paperList = [ObjectId(Item) for Item in paperList]
        for paperItem in paperList:
            paper = utils.getPaperByid(paperItem, paperCol)[0]
            paperId = paper["_id"]
            try:
                with open("configure/paperRef1.conf", "r") as f:
                    current_model_id = f.readline().replace("\n", "").strip()  # 模型id
                    current_paper_id = f.readline().replace("\n", "").strip()  # 论文id
                    # 若已读取过该文章，跳过
                    if (paperId < ObjectId(current_paper_id)):
                        continue
            except:
                print("no current_paper_id yet")
                current_paper_id = ""
                sys.stdout.flush()

            try:
                queryStr = "REF( " + paper["eid"] + " )  AND  PUBYEAR  > 2020  AND  PUBYEAR  < 2023"
            except:
                continue
            citedByItemNum = citeSearchNum(queryStr)
            
            # 若无引用
            if ( citedByItemNum == 0 ):
                continue
            # 不需要添加
            # if (citedByItemNum <= citedByCount):
            #     print("cite hasn't changed")
            #     sys.stdout.flush()

            # 需要添加
            # else:
            # print("cite should get changed")
            sys.stdout.flush()
            citedByItems = citeSearch(queryStr)
            try:
                citings = paper["citings"]
            except:
                citings = []
                paper["citings"] = citings

            for cite in citedByItems:
                if (len(citings) == citedByItemNum):
                    break
                # 去重
                dupResult = utils.getDuplication(paperCiteCol, cite)
                if dupResult == None:
                    # 若未出现重复内容，则将引用插入数据库并记录id号，插入paper的citings中
                    inResult = paperCiteCol.insert_one(cite)
                    citings.append(inResult.inserted_id)
                else:
                    # 若出现了重复内容，匹配citing对应的id号，并插入paper的citings中
                    # eid = cite["eid"]
                    # id = utils.findIdByEid(eid, paperCiteCol)
                    id = dupResult
                    if id not in citings:
                        citings.append(id)

            citedByCount = len(citings)
            paperCol.update_one({"_id": paper["_id"]}, {'$set': {"citings": citings, "citedby-count": citedByCount}})

            # 记录
            with open("configure/paperRef1.conf", "w") as f:
                f.write(str(modelId) + "\n")
                f.write(str(paperId) + "\n")
            print("******************* next paper *********************")
            sys.stdout.flush()

if __name__ == "__main__":
    run()