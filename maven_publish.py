#!/usr/bin/python
# -*- coding:UTF-8 -*-

from xml.dom.minidom import parse
import xml.dom.minidom
import os
import sys
import logging
import logging.handlers
import ConfigParser

reload(sys)
sys.setdefaultencoding('utf-8')

LOG_FILE = 'info.log'
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
conf = {}

MSG_OK = "OK"
MSG_FAIL = "FAIL"

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
解析pom文件
'''	
def handlePOM(dir,name):		
	# 使用minidom解析器打开XML文档
	try:
		DOMTree = xml.dom.minidom.parse(os.path.join(dir,name))
	except Exception as e:
		logger.error("解析XML文件失败失败%s%s\t%s" % (dir,name,e))
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

	publish(dir,name,artifactId,version,groupId)
'''
验证jar是否存在
	存在返回路径
	不存在返回None
'''
def getPublishJar(path,filename):
	jarPath = os.path.join(path,filename.replace(".pom",".jar"))
	
	if os.path.exists(jarPath):
		return jarPath
	else:
		return None
'''
发布
'''
def publish(path,filename,artifactId,version,groupId):
	msg = MSG_OK
	if artifactId == "" or groupId == "" or version == "":
		msg = MSG_FAIL
	## 路径
	fullname = os.path.join(path,filename)

	mvnStr = "mvn deploy:deploy-file -DgroupId=%s -DartifactId=%s -Dversion=%s -Dpackaging=%s -DrepositoryId=%s -Dfile=%s -Durl=%s -DgeneratePom=%s"
	
	################
	# 先提交jar
	################
	jarPath = getPublishJar(path,filename)
	if jarPath != None:
		# 发布jar
		mvnJarStr = mvnStr % (groupId,artifactId,version,"jar",getConfig("repositoryId"),jarPath,getConfig("url"),getConfig("generatePom"))
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
'''
目录检索回调
参数：
arg 		同os.path.walk中的第三个参数
dirname		目录
names
'''
def visit(arg,dirname,names):
	for name in names:
		if name.endswith(".pom"):
			handlePOM(dirname,name)
'''
写入空配置文件
'''
def writeConfig():
	cf = ConfigParser.ConfigParser()
	cf.add_section("global")
	cf.set("global","url","Your repository Url,like http://xxx/maven2/repository")
	cf.set("global","repositoryId","Your repositoryId,must match with maven pom.xml")
	cf.set("global","generatePom","false")
	with open(CONFIG_FILE_NAME,"w+") as f:
		cf.write(f)
'''
读取配置信息
'''
def readConfig():
	if not os.path.exists(CONFIG_FILE_NAME):
		writeConfig()
		return False
	config = ConfigParser.ConfigParser();
	config.read(CONFIG_FILE_NAME)

	confUrl = config.get("global","url") or ""
	if confUrl.startswith("Your"):
		doPrint("请填写配置文件，路径为：当前目录/%s" % CONFIG_FILE_NAME)
		sys.exit()

	conf["url"] =confUrl
	conf["repositoryId"] = config.get("global", "repositoryId") or ""
	conf["generatePom"] = config.get("global", "generatePom") or ""
	return True
'''
获取配置
'''
def getConfig(str):
	if conf == {}:
		readConfig()
	return conf[str]
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
	if len(sys.argv) == 2:
		dir = sys.argv[1]
	# print dir
	if dir != None:
		dirSearch(dir)
	# handlePOM("d:/t","spring-cloud-netflix-dependencies-1.3.5.RELEASE.pom")
#############TODO
# 1、多线程
# 2、记录已提交，防止重复提交，提升效率