import os
import sys

import pymongo.errors

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))
import utils.utils as utils
import json
import requests
import datetime
import time
from dateutil import parser
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')  # Change default encoding to utf8
import requests.packages.urllib3.util.ssl_
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL'
from bson.objectid import ObjectId
from bs4 import BeautifulSoup

# 设置数据库
ip = "172.21.213.214"
port = 27017
dbName = "ModelDB"
# dbName = "ModelDB2"
modelCol = utils.mongoConnect4(ip, port, dbName, "model240111")
patentCol = utils.mongoConnect4(ip, port, dbName, "Patent0912")
patentCiteCol = utils.mongoConnect4(ip, port, dbName, "PatentCite0912")
# 数据爬取页数
pageSize = 25
# 爬取论文网站
scopusUrl = "https://api.elsevier.com/content/search/scopus"
sciUrl = "https://api.elsevier.com/content/search/sciencedirect"
api_key_num = 0
scopusSearch_starttime = datetime.datetime.now()

def run():
    for patent in patentCol.find().sort("_id", 1):

        # 记录爬取到的位置配置文件
        patentId = patent["_id"]
        # 读取当前配置文件（读到哪篇文章了）
        try:
            with open("../configure/patentRef.conf", "r") as f:
                current_patent_id = f.readline().replace("\n", "").strip()  # 论文id
                if (patentId < ObjectId(current_patent_id)):
                    continue
        except:
            print("no config file yet")
            sys.stdout.flush()

        patent_url = "https://patents.google.com/patent/" + patent["pubNum"]
        print(patent_url)
        sys.stdout.flush()
        patent_page = requests.get(patent_url, verify=False, timeout=30, headers=utils.getHeaders())
        patent_page.encoding = "utf-8"
        patent_soup = BeautifulSoup(patent_page.text, "lxml")
        # 获取施引专利
        citedByOrig = patent_soup.select("tr[itemprop='forwardReferencesOrig']")
        citedByFamily = patent_soup.select("tr[itemprop='forwardReferencesFamily']")
        citings = patent["citings"]
        for r in range(0, 2):
            citedBy = citedByOrig if r == 0 else citedByFamily
            if citedBy != None:
                for cited in citedBy:
                    citedPubNum = cited.select("td a span[itemprop='publicationNumber']")[0].text
                    # 查询数据库是否存在该施引文献
                    docSize = utils.getQueryResultNum(patentCiteCol, {"pubNum": citedPubNum})
                    if docSize == 0:
                        citedLanguage = cited.select("td a span[itemprop='primaryLanguage']")[0].text
                        citedPriorDate = cited.select("td[itemprop='priorityDate']")[0].text
                        citedPubDate = cited.select("td[itemprop='publicationDate']")[0].text
                        OriAssignee = cited.select("td span[itemprop='assigneeOriginal']")
                        citedOriAssignee = "" if len(OriAssignee) == 0 else OriAssignee[0].text
                        citedTitle = cited.select("td[itemprop='title']")[0].text
                        citePub = {
                            "pubNum": citedPubNum,
                            "title": citedTitle,
                            "oriAssignee": citedOriAssignee,
                            "language": citedLanguage,
                             "priorDate": utils.parseTime(citedPriorDate),
                            "pubDate": utils.parseTime(citedPubDate),

                        }
                        inResult = patentCiteCol.insert_one(citePub)

                        citing = {
                            "_id": inResult.inserted_id,
                            "type": "Orig" if r == 0 else "Family"
                        }
                        citings.append(citing)
        patentCol.update_one({"_id": patent["_id"]}, {'$set': {"citings": citings}})

        # 写入爬取配置文件
        with open("../configure/patentRef.conf", "w") as f:
            f.write(str(patentId) + "\n")
        print("已更新"+str(patentId))
        print("******************* next patent *********************")
        sys.stdout.flush()

def tryAgain():
    try:
        run()
    except Exception as e:
        if e == pymongo.errors.CursorNotFound or requests.exceptions.ProxyError:
            return e
        return 0

if __name__ == "__main__":
    B = True
    while B:
        time.sleep(60)
        e = tryAgain()
        if e != 0:
            with open("../configure/patentRefErrors.conf", "w") as f:
                f.write(str(e) + "\n")
        else:
            B = False
