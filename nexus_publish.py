#!/usr/bin/python
# -*- coding:UTF-8 -*-

# 导入实除法模块后的结果为浮点数
from __future__ import division 
from xml.dom.minidom import parse
from Queue import Queue
from time import time
import xml.dom.minidom
import os
import io
import sys
import json
import logging
import logging.handlers
import ConfigParser
import threading
q = Queue()
threadLock = threading.Lock()
reload(sys)
sys.setdefaultencoding('utf-8')

'''
检测目录结构
'''
def checkDir():
    isLogExist = os.path.exists('log')

    if not isLogExist:
        os.makedirs('log')
        
checkDir()

LOG_FILE = 'log/info.log'
fileHandler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes = 1024* 1024, backupCount = 5)
consoleHandler = logging.StreamHandler()
# fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s -%(message)s'
fmt = '%(asctime)s :: %(message)s'
formatter = logging.Formatter(fmt)
fileHandler.setFormatter(formatter)
logger = logging.getLogger('maven_publish')
consoleHandler.setLevel(logging.DEBUG)
consoleHandler.setFormatter(formatter)
logger.addHandler(fileHandler)
logger.addHandler(consoleHandler)
logger.setLevel(logging.INFO)

CONFIG_FILE_NAME = "config.ini"
'''
仓库类型，默认为maven，可选值为: maven npm
'''
repositoryType = 'maven'
conf = {}
conf['maven'] = {}
conf['npm'] = {}

MSG_OK = "OK"
MSG_FAIL = "FAIL"

itemSize = 0
passedSize = 0
startTime = 0
endTime = 0
'''
获取一组文本值
'''
def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.nodeValue)
    return ''.join(rc)
'''
获取下一级元素
'''
def getFirstLevelChildNodes(node,type):
    list = []
    if node == None:
        return list
    children = node.childNodes
    for child in children:
        if child.parentNode == node:
            if type == -1 or type == child.nodeType:
                list.append(child)
    return list
'''
获取下一级元素
'''
def filterFirstLevelChildNodes(node,nodeName):
    list = []
    if node == None:
        return list
    children = node.childNodes
    for child in children:
        if child.parentNode == node:
            if nodeName == "" or nodeName == child.nodeName:
                list.append(child)
    return list
'''
根据标签查找节点
'''
def searchNodes(node, tagName):
    list = []
    if node == None:
        return list
    return node.getElementsByTagName(tagName)
    
def getValue(element):
    return element == None and "" or element.firstChild.nodeValue
'''
获取属性
'''
def getPropties(project):
    result = {}
    len = project.getElementsByTagName("properties").length
    if len == 1:
        properties = project.getElementsByTagName("properties")[0].childNodes
        for prop in properties:
            if prop.nodeType == prop.ELEMENT_NODE and prop.firstChild != None:
                result[prop.nodeName] = prop.firstChild.nodeValue
    return result
'''
验证maven发布结果
'''
def mvnResultCheck(a):
    mvnStr = ""
    if a == None:
        return MSG_FAIL
    if isinstance(a,str):
        mvnStr = a
    elif isinstance(a,list):
        mvnStr = "".join(str(x) for x in a)
    try:
        mvnStr.index("BUILD SUCCESS")
        return MSG_OK
    except Exception as e:
        return MSG_FAIL
'''
验证npm发布结果
'''
def npmResultCheck(a):
    aStr = ""
    if a == None:
        return MSG_FAIL
    if isinstance(a,str):
        aStr = a
    elif isinstance(a,list):
        aStr = "".join(str(x) for x in a)
    try:
        if aStr.find('+') > -1:
            print aStr            
            return MSG_OK
        elif aStr.index('npm adduser') > -1:
            print '需要先在本机执行 npm adduser 登陆才可以发布'
            sys.exit()
    except Exception as e:
        return MSG_FAIL
'''
npm提交
'''
def handleNPM(dir):
    npmStr = 'npm publish %s --registry %s'
    resultStr = npmStr % (dir,getConfig("url"))
    # 处理package.json
    checkPackagejson(dir)
    msg = npmResultCheck(os.popen(resultStr).readlines())
    logger.info("%s\t%s\t%s" % (msg,dir,resultStr))
'''
处理package.json文件，清除scripts.prepublish
'''
def checkPackagejson(dir):
    load_dict=None
    package_name='package.json'
    with io.open(os.path.join(dir,package_name),'r',encoding='utf-8') as load_f:
        load_dict=json.load(load_f)
        try:
            load_dict['scripts']['prepublish']
            load_dict['scripts'].pop('prepublish')
        except Exception as e:
            return
    with io.open(os.path.join(dir,package_name),'w',encoding='utf-8') as save_f:
        save_f.write(unicode(json.dumps(load_dict, ensure_ascii=False)))
'''
解析pom文件
'''    
def handlePOM(dir,name):        
    # 使用minidom解析器打开XML文档
    try:
        DOMTree = xml.dom.minidom.parse(os.path.join(dir,name))
    except Exception as e:
        logger.error("解析XML文件失败失败%s/%s\t%s" % (dir,name,e))
        return
    project = DOMTree.documentElement
    props = {}
    try:
        props = getPropties(project)
    except Exception as e:
        logger.error("解析<properties>失败%s%s\t%s" % (dir,name,e))
    #print props['archaius.version']
    #####变量
    artifactId = ""
    version = ""
    groupId = ""

    ## artifactId
    artifactIdLen = len(filterFirstLevelChildNodes(project,"artifactId"))
    if artifactIdLen > 0:
        artifactId = getValue(filterFirstLevelChildNodes(project,"artifactId")[0])
    ### parent
    parent = None
    parents = filterFirstLevelChildNodes(project,"parent")
    if len(parents) == 1:
        parent = parents[0]

    ## version
    versionLen = len(filterFirstLevelChildNodes(project,"version"))
    if versionLen > 0:
        version = getValue(filterFirstLevelChildNodes(project,"version")[0])
    else:
        if parent != None:
            version = getValue(filterFirstLevelChildNodes(parent,"version")[0])
    ## groupId
    groupIdLen = len(filterFirstLevelChildNodes(project,"groupId"))
    if groupIdLen > 0:
        groupId = getValue(filterFirstLevelChildNodes(project,"groupId")[0])
    else:
        if parent != None:
            groupId = getValue(filterFirstLevelChildNodes(parent,"groupId")[0])
    ## classifier
    profilesLen = len(filterFirstLevelChildNodes(project,"profiles"))
    
    if profilesLen > 0:
        classifiers = searchNodes(project, "classifier")
        for classifier in classifiers:
            publishMvn(dir,name,artifactId,version,groupId, getValue(classifier))
        return
    publishMvn(dir,name,artifactId,version,groupId, None)
'''
验证jar是否存在
    存在返回路径
    不存在返回None
'''
def getPublishJar(path,filename, classifier):
    prefix = ".jar"
    if classifier != None:
        prefix = "-" + classifier + prefix
    jarPath = os.path.join(path,filename.replace(".pom", prefix))
    
    if os.path.exists(jarPath):
        return jarPath
    else:
        return None
'''
发布
'''
def publishMvn(path,filename,artifactId,version,groupId, classifier):
    msg = MSG_OK
    if artifactId == "" or groupId == "" or version == "":
        msg = MSG_FAIL
    ## 路径
    fullname = os.path.join(path,filename)

    mvnStr = "mvn deploy:deploy-file -DgroupId=%s -DartifactId=%s -Dversion=%s -Dpackaging=%s -DrepositoryId=%s -Dfile=%s -Durl=%s -DgeneratePom=%s"
    
    ################
    # 先提交jar
    ################
    jarPath = getPublishJar(path,filename, classifier)
    if jarPath != None:
        # 发布jar
        mvnJarStr = mvnStr % (groupId,artifactId,version,"jar",getConfig("repositoryId"),jarPath,getConfig("url"),getConfig("generatePom"))
        if classifier != None:
            mvnJarStr += " -Dclassifier=" + classifier
        msg = mvnResultCheck(os.popen(mvnJarStr).readlines())
        logger.info("%s\t%s\t%s\t%s\t%s\t%s" % (artifactId,version,groupId,jarPath,msg,mvnJarStr))
    ################
    # 再提交pom
    ################
    mvnPomStr = mvnStr % (groupId,artifactId,version,"pom",getConfig("repositoryId"),fullname,getConfig("url"),getConfig("generatePom"))
    msg = mvnResultCheck(os.popen(mvnPomStr).readlines())
    logger.info("%s\t%s\t%s\t%s\t%s\t%s" % (artifactId,version,groupId,fullname,msg,mvnPomStr))
'''
目录搜索
'''
def dirSearch(dir):
    os.path.walk(dir,visit,[])
    global itemSize
    itemSize = len(q.queue)
    conMaxThread = getConfig("maxThread")
    threadSize = min(itemSize, conMaxThread)

    logger.info("待发布依赖数量为【%s】,启动线程个数为【%s】" % (itemSize, threadSize))
    for i in range(threadSize):
        # threadName = "Thread-%s" % i
        myThread(i).start()
'''
创建类
'''
class myThread(threading.Thread):
    def __init__(self,threadID):
        threading.Thread.__init__(self)
        self.threadID = threadID
    def run(self):
        while not q.empty():
            try:
                threadLock.acquire()
                item = q.get()
                
                threadLock.release()
                if repositoryType == 'maven':
                    handlePOM(item[0], item[1])
                elif repositoryType == 'npm':
                    handleNPM(item[0])
                global passedSize
                passedSize+=1
                #passedSize = itemSize - len(q.queue)
                per = 0
                if itemSize != 0:
                    per = passedSize / itemSize * 100
                doPrint("当前进度[%s / %s] %.2f%%" % (passedSize, itemSize, per))
            except Exception as e:
                print e
        recordDone()
'''
结束后记录
'''
def recordDone():
    if endTime != 0:
        return
    global endTime
    endTime = int(time())
    passedTime = endTime - startTime
    logger.info("依赖共上传【%s】个,用时 %d秒" % (itemSize,passedTime))
'''
目录检索回调
参数：
arg         同os.path.walk中的第三个参数
dirname        目录
names
'''
def visit(arg,dirname,names):
    for name in names:
        if repositoryType == 'maven':
            if name.endswith(".pom"):
                # handlePOM(dirname,name)
                q.put([dirname, name])
        if repositoryType == 'npm' and name == 'package.json':
            q.put([dirname, name])
    
'''
写入空配置文件
'''
def writeConfig():
    cf = ConfigParser.ConfigParser()
    cf.add_section("maven")
    cf.set("maven","url","Your maven repository Url,like http://xxx/maven2/repository")
    cf.set("maven","repositoryId","Your maven repositoryId,must match with maven pom.xml")
    cf.set("maven","generatePom","false")
    cf.set("maven","maxThread", 10)
    cf.add_section("npm")
    cf.set("npm","url","Your npm repository Url,like http://xxx/npm/repository")
    with open(CONFIG_FILE_NAME,"w+") as f:
        cf.write(f)
'''
读取配置信息
'''
def readConfig():
    if not os.path.exists(CONFIG_FILE_NAME):
        writeConfig()
        return False
    if repositoryType == 'maven':
        return readMavenConfig()
    elif repositoryType == 'npm':
        return readNpmConfig()
        
def safeReadConfig(config, item, option):
    try:
        return config.get(item, option)
    except Exception as e:
        return ''
'''
读取maven配置
'''
def readMavenConfig():
    config = ConfigParser.ConfigParser();
    config.read(CONFIG_FILE_NAME)

    confUrl = safeReadConfig(config, "maven","url")
    if confUrl.startswith("Your"):
        doPrint("请填写配置文件，路径为：当前目录/%s" % CONFIG_FILE_NAME)
        sys.exit()
    conf[repositoryType]["url"] = confUrl
    conf[repositoryType]["repositoryId"] = safeReadConfig(config, "maven", "repositoryId")
    conf[repositoryType]["generatePom"] = safeReadConfig(config, "maven", "generatePom")
    conf[repositoryType]["maxThread"] = int(safeReadConfig(config, "maven", "maxThread") or "10")
    return True
'''
读取npm配置
'''
def readNpmConfig():
    config = ConfigParser.ConfigParser();
    config.read(CONFIG_FILE_NAME)

    confUrl = safeReadConfig(config, "npm","url")
    if confUrl.startswith("Your"):
        doPrint("请填写配置文件，路径为：当前目录/%s" % CONFIG_FILE_NAME)
        sys.exit()
    conf[repositoryType]["url"] = confUrl
    conf[repositoryType]["maxThread"] = safeReadConfig(config,"npm","maxThread") or "10"
    return True
    
'''
获取配置
'''
def getConfig(str):
    if conf[repositoryType] == {}:
        readConfig()
    try:
        return conf[repositoryType][str]
    except Exception as e:
        return ''

'''
控制台输出，处理编码问题，
涉及到中文的输出可以调用
'''
def doPrint(str):
    if str == None:
        return
    print str.decode("UTF-8").encode(sys.stdin.encoding)

if __name__=="__main__":
    ifConfig = readConfig()
    if not ifConfig:
        doPrint("错误：必须填写配置信息。配置文件路径：当前目录/%s" % CONFIG_FILE_NAME)
        sys.exit()
    dir = None
    if len(sys.argv) > 1:
        dir = sys.argv[1]
    if len(sys.argv) > 2:
        repositoryType = sys.argv[2]
    # print dir
    if dir != None:
        global startTime
        startTime = int(time())
        dirSearch(dir)
    else:
        print 'Usage: python nexus_publish.py [dir] [type(maven|npm)]'
    # handlePOM("d:/t","spring-cloud-netflix-dependencies-1.3.5.RELEASE.pom")
#############TODO
# 1、多线程
# 2、记录已提交，防止重复提交，提升效率