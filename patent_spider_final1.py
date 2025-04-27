import requests
import json
from bs4 import BeautifulSoup
import urllib
import datetime
import urllib3
urllib3.disable_warnings()



import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/'+'..'))
import utils.utils as utils


class Patent():

    fullName = ""
    abbrev = ""

    ip = "172.21.213.33"
    port = 27017
    dbName = "ModelDB"

    collection = utils.mongoConnect4(ip,port,dbName,"Patent0912")
    citeCol = utils.mongoConnect4(ip,port,dbName,"PatentCite0912")
    modelCol = utils.mongoConnect4(ip,port,dbName,"model231220")

    def readInfo(self,model,patentSimple,patent_url):
        containsFullName = False
        go = False
        while go == False:
            try:
                patent_page = requests.get(patent_url,verify=False,timeout=30, headers = utils.getHeaders())
                patent_page.encoding = "utf-8"
                patent_soup = BeautifulSoup(patent_page.text, "lxml")
                if utils.AinB(self.fullName,patent_page.text): # 网页是否包含模型全称
                    containsFullName = True
                if not utils.AinB("Your Browser Isn't Supported By Google Patents",patent_page.text):
                    go = True
            except Exception as e:
                print(str(e))

        reference = patent_soup.select("tr[itemprop='backwardReferences']")
        referenceList = []
        for ref in reference:
            ref_pubNum = ref.select("span[itemprop='publicationNumber']")
            if ref_pubNum != []:
                ref_pubNum = ref_pubNum[0].text
            ref_priorityDate = ref.select("td[itemprop='priorityDate']")
            if ref_priorityDate != []:
                ref_priorityDate = ref_priorityDate[0].text
            ref_publicationDate = ref.select("td[itemprop='publicationDate']")
            if ref_publicationDate != []:
                ref_publicationDate = ref_publicationDate[0].text
            ref_assigneeOriginal = ref.select("span[itemprop='assigneeOriginal']")
            if ref_assigneeOriginal != []:
                ref_assigneeOriginal = ref_assigneeOriginal[0].text
            ref_title = ref.select("td[itemprop='title']")
            if ref_title != []:
                ref_title = ref_title[0].text
            refObj = {
                "pubNum": ref_pubNum,
                "priorityDate": ref_priorityDate,
                "publicationDate": ref_publicationDate,
                "assigneeOriginal": ref_assigneeOriginal,
                "title": ref_title
            }
            referenceList.append(refObj)
            

        # if containsFullName == True:
        # 入库
        article = patent_soup.select("article")[0]
        title = article.select("span[itemprop='title']")[0].text.replace("\n","").strip()
        pubNum = article.select("dl dd[itemprop='publicationNumber']")[0].text
        authorityCountryCode = article.select("dl dd[itemprop='countryCode']")[0].text
        authorityCountryName = article.select("dl dd[itemprop='countryName']")[0].text
        descriptionList = article.select("div[class='description-paragraph']")
        desTextList = []
        for d in descriptionList:
            desTextList.append(d.text)
        claimList = article.select("div[class='claim-text']")
        claimTextList = []
        for c in claimList:
            claimTextList.append(c.text)
        priorArtKeywords = article.select("dl dd[itemprop='priorArtKeywords']")
        keywords = []
        for key in priorArtKeywords:
            keywords.append(key.text)
        # priorArtDate = article.select("dl dd time[itemprop='priorArtKeywords']")[0].text
        applicationNumber = article.select("dd[itemprop='applicationNumber']")[0].text
        inventor = article.select("dd[itemprop='inventor']")
        inventors = []
        for inv in inventor:
            inventors.append(inv.text)
        originalAssignee = article.select("dd[itemprop='assigneeOriginal']")
        originalAssignee = originalAssignee[0].text if len(originalAssignee)>0 else ""
        if utils.keyInJson("priority_date", patentSimple):
            priorityDate = patentSimple["priority_date"]
        else:
            priorityDateEle = article.select("dd time[itemprop='priorityDate']")
            priorityDate = priorityDateEle[0].text if len(priorityDateEle)>0 else None
        
        if utils.keyInJson("filling_date", patentSimple):
            filingDate = patentSimple["filling_date"]
        else:
            filingDate = article.select("dd time[itemprop='filingDate']")
            filingDate = filingDate[0].text if len(filingDate)>0 else ""

        if utils.keyInJson("publication_date", patentSimple):
            publicationDate = patentSimple["publication_date"]
        else:
            publicationDate = article.select("dd time[itemprop='publicationDate']")[0].text
        
        if utils.keyInJson("grant_date", patentSimple): 
            grantDate = patentSimple["grant_date"]

        publication = {
            "title":title,
            "pubNum":pubNum,
            "authCountryCode":authorityCountryCode,
            "authCountryName":authorityCountryName,
            "priorArtKeywords":keywords,
            "applicationNumber":applicationNumber,
            "inventors":inventors,
            "oriAssignee":originalAssignee,
            "priorityDate":priorityDate,
            "filingDate":filingDate,
            "publicationDate":publicationDate,
            "grantDate":grantDate,
            "descriptionList":desTextList,
            "claimList":claimTextList,
            "referenceList":referenceList,
        }

        num = utils.getQueryResultNum(self.collection,{"pubNum":pubNum})
        if num == 0 :# 不存在该专利，插入
            
            # 获取施引专利
            citedByOrig = patent_soup.select("tr[itemprop='forwardReferencesOrig']")
            citedByFamily = patent_soup.select("tr[itemprop='forwardReferencesFamily']")
            citings = []
            for r in range(0,2):
                citedBy = citedByOrig if r == 0 else citedByFamily
                if citedBy != None:                   
                    for cited in citedBy:
                        citedPubNum = cited.select("td a span[itemprop='publicationNumber']")[0].text
                        # 查询数据库是否存在该施引文献
                        docSize = utils.getQueryResultNum(self.citeCol,{"pubNum":citedPubNum})
                        if docSize == 0:
                            citedLanguage = cited.select("td a span[itemprop='primaryLanguage']")[0].text
                            citedPriorDate = cited.select("td[itemprop='priorityDate']")[0].text
                            citedPubDate = cited.select("td[itemprop='publicationDate']")[0].text
                            OriAssignee = cited.select("td span[itemprop='assigneeOriginal']")
                            citedOriAssignee = "" if len(OriAssignee)==0 else OriAssignee[0].text
                            citedTitle = cited.select("td[itemprop='title']")[0].text
                            citePub = {
                                "pubNum":citedPubNum,
                                "title":citedTitle,
                                "oriAssignee":citedOriAssignee,
                                "language":citedLanguage,
                                "priorDate":utils.parseTime(citedPriorDate),
                                "pubDate":utils.parseTime(citedPubDate), 
                                                  
                            }                       
                            inResult = self.citeCol.insert_one(citePub)

                            citing = {
                                "_id":inResult.inserted_id,
                                "type":"Orig" if r == 0 else "Family"
                            }
                            citings.append(citing)
            publication["citings"] = citings

            inResult = self.collection.insert_one(publication)

            patentList = []
            if utils.keyInJson("patentList_FN",model):
                patentList = model["patentList_FN"]
            patentList.append(inResult.inserted_id)
            model["patentList_FN"] = patentList
            #update
            self.modelCol.update_one({"_id":model["_id"]},{"$set":{"patentList_FN":patentList}})
        return model
        
    def run(self,modelList):

        nextModel = True
        for model in self.modelCol.find().sort("_id",-1):

            dates = ["20210101","20221231"]

            # 模型id 简称 全称
            Id = str(model["_id"])
            self.fullName = model["full"].strip()
            self.abbrev = model["abbrev"].strip()

            try:
                with open("patent/patent1.conf","r") as f:
                    modelId = f.readline().replace("\n","").strip()
                    startDate = f.readline().replace("\n","")
                    endDate = f.readline().replace("\n","")
                    count = f.readline().replace("\n","")

                    if startDate == "finish":
                        dateIndex = 0
                        count = 0
                    else :       
                        count = int(count)                
                        for d in range(0,len(dates)-1):
                            if dates[d] == startDate:
                                dateIndex = d
                            
                                if dates[d+1] == endDate:                           
                                    break
                                else:
                                    dates.insert(d+1, endDate)
                                    break
                            else:
                                stamp1 = utils.convertStrToTimestamp(dates[d])
                                stamp2 = utils.convertStrToTimestamp(dates[d+1])
                                stampStart = utils.convertStrToTimestamp(startDate)
                                if stampStart > stamp1 and stampStart < stamp2:
                                    dates.insert(d+1, startDate)
                                    dateIndex = d+1
                                    if dates[d+2] == endDate:
                                        break
                                    else:
                                        dates.insert(d+2, endDate)      
                                        break                     
                    if nextModel == True and (modelId == '' or modelId == Id):
                        nextModel = False
            except:
                dateIndex = 0
                count = 0
                nextModel = False

            if nextModel:
                continue


            if self.fullName != "" and self.abbrev != "":
                query = 'q="'+self.fullName+'"'# + ' OR ('+self.abbrev+' Model)'
            elif self.fullName != "":
                query = 'q="'+self.fullName+'"'
            elif self.abbrev != "":
                query = 'q='+self.abbrev+' Model'


            query = query.replace(" ","+").replace(",","")
            
            print(query)

            query = urllib.parse.quote_plus(query) # 查询语句
        
            # for dateIndex in range(startIndex,len(dates)):\
            # dateIndex = 0
            while dateIndex < len(dates)-1:                
                
                page = int(count/10) # 列表当前页数
                before = "publication:"+dates[dateIndex+1]
                after = "publication:"+dates[dateIndex]
                urlBase = "https://patents.google.com/xhr/query?url="+query+"%26before="+before+"%26after="+after+"%26status=GRANT%26type=PATENT%26" # %26language=ENGLISH
                url = urlBase + "page="+str(page)+"&exp="

                response = utils.getResponse(url,None)
                # print(response.text)
                response_json = json.loads(response.text)
                total_num_pages = response_json["results"]["total_num_pages"]
                total_num_results = response_json["results"]["total_num_results"]
                if total_num_results > 1000: #超过1000则缩小时间范围
                    if len(dates) == 2:
                        dates.insert(1,"19700101")
                    else:
                        try:
                            midDate = utils.getMidDate(dates[dateIndex],dates[dateIndex+1])
                            dates.insert(dateIndex+1, midDate)
                        except:
                            break
                    continue
                with open("patent/patent1.conf","w") as f:
                    f.write(Id+"\n")
                    f.write(dates[dateIndex]+"\n")
                    f.write(dates[dateIndex+1]+"\n")
                    f.write(str(count))

                for i in range(total_num_pages):
                    if i == 0:
                        patents_json = response_json
                    else:
                        page = i
                        url = urlBase + "page="+str(page)+"&exp="
                        while True:
                            try:
                                with requests.get(url,verify=False,timeout=30, headers = utils.getHeaders()) as response:
                                    patents_json = json.loads(response.text)
                                break
                            except:
                                continue
                    results = patents_json["results"]["cluster"][0]["result"]
                    for p in range(count%10,len(results)):
                        patent = results[p]
                        patent_url = "https://patents.google.com/patent/"+patent["patent"]["publication_number"]
                        print(str(count) + " " + patent_url)
                        # try:
                        model = self.readInfo(model, patent["patent"], patent_url)
                        # except:
                        #     error_pubNums.append(patent["patent"]["publication_number"])
                        #     continue
                        count += 1
                        with open("patent/patent1.conf","w") as f    :
                            f.write(Id+"\n")
                            f.write(dates[dateIndex]+"\n")
                            f.write(dates[dateIndex+1]+"\n")
                            f.write(str(count))
                count = 0
                dateIndex += 1

            # utils.updateModelInfo(abbreviation,"patent",self.collection.estimated_document_count())
            # utils.updateModelInfo(abbreviation,"patent_cite",self.citeCol.estimated_document_count())

            with open("patent/patent1.conf","w") as f:
                f.write(Id+"\n")
                f.write("finish\n")
                f.write("finish\n")
                f.write("finish\n")

if __name__ == '__main__':

    patent = Patent()
    patent.run(utils.getModelList())


