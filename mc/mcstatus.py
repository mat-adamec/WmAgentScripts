#!/usr/bin/env python -w
#TODO: # of wf acquired/running group by zone
import sys,urllib,urllib2,re,time,os
import simplejson as json
import optparse
import httplib
import datetime
import shutil

dashost = 'https://cmsweb.cern.ch'
reqmgrsocket='vocms204.cern.ch'
overview = ''

def getDurationByZoneTeam(reqinfo,status,team):
	duration = {'FNAL':0,'RAL':0,'CNAF':0,'IN2P3':0,'ASGC':0,'KIT':0,'PIC':0,'no_cust':0}
	for workflow in reqinfo.keys():
		for t in reqinfo[workflow]['team']:
			if reqinfo[workflow]['status'] == status and t == team:
				z = reqinfo[workflow]['zone']
				d = reqinfo[workflow]['duration']
				duration[z] += d
	return duration
	
def getzonebyt1(s):
	custodial = 'no_cust'
	if not s:
		return custodial
	t1list = {'T1_FR_CCIN2P3':'IN2P3','T1_TW_ASGC':'ASGC','T1_IT_CNAF':'CNAF','T1_US_FNAL':'FNAL','T1_DE_KIT':'KIT','T1_ES_PIC':'PIC','T1_UK_RAL':'RAL'}
	for i in t1list.keys():
		if i in s:
			custodial = t1list[i]
	return custodial

def getWorkflowInfo(workflow):
	conn  =  httplib.HTTPSConnection('cmsweb.cern.ch', cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
	r1=conn.request('GET','/reqmgr/view/showWorkload?requestName=' + workflow)
	r2=conn.getresponse()
	data = r2.read()
	conn.close()
	list = data.split('\n')

	primaryds = ''
	priority = -1
	timeev = -1
	prepid = ''
	sites = []
	for raw in list:
		if 'primaryDataset' in raw:
			primaryds = raw[raw.find("'")+1:]
			primaryds = primaryds[0:primaryds.find("'")]
		if 'PrepID' in raw:
			prepid = raw[raw.find("'")+1:]
			prepid = prepid[0:prepid.find("'")]
		elif 'TimePerEvent' in raw:
                        a = raw.find("'")
                        if a >= 0:
                                b = raw.find("'",a+1)
                                timeev = int(raw[a+1:b])
                        else:
                                a = raw.find(" =")
                                b = raw.find('<br')
                                timeev = int(float(raw[a+3:b]))
		elif 'request.priority' in raw:
			a = raw.find("'")
			if a >= 0:
				b = raw.find("'",a+1)
				priority = int(raw[a+1:b])
			else:
				a = raw.find(" =")
				b = raw.find('<br')
				#print "*%s*" % raw[a+3:b]
				priority = int(raw[a+3:b])
		elif 'sites.whitelist' in raw and not '[]' in raw:
			sites = '['+raw[raw.find("[")+1:raw.find("]")]+']'	
			sites = eval(sites)		
	custodialt1 = 'no_cust'
	for i in sites:
		if 'T1_' in i:
			custodialt1 = i
			break

	conn  =  httplib.HTTPSConnection('cmsweb.cern.ch', cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
	r1=conn.request('GET','/reqmgr/reqMgr/request?requestName=' + workflow)
	r2=conn.getresponse()
	data = r2.read()
	s = json.loads(data)
	conn.close()
	try:
		filtereff = float(s['FilterEfficiency'])
	except:
		filtereff = -1
	try:
		team = s['Assignments']
	except:
		team = []
	try:
		type = s['RequestType']
	except:
		type = ''
	try:
		status = s['RequestStatus']
	except:
		status = ''
	try:
                reqevts = s['RequestSizeEvents']
        except:
                try:
                        reqevts = s['RequestNumEvents']
                except:
                        print "No RequestNumEvents for this workflow: "+workflow
                        return ''
	try:
		inputdataset = s['InputDatasets'][0]
	except:
		inputdataset = ''
	
	if type in ['MonteCarlo']:
		expectedevents = int(reqevts)
	elif type in ['MonteCarloFromGEN']:
		[ie,ist] = getdsdetail(inputdataset)
		expectedevents = int(filtereff*ie)
	else:
		expectedevents = -1
	
	j = {}
	k = {'success':'success','failure':'failure','Pending':'pending','Running':'running','cooloff':'cooloff','pending':'queued','inWMBS':'inWMBS','total_jobs':'total_jobs','local_queue':'local_queue'}
	for r in overview:
		if r['request_name'] == workflow:
			break
	if r:
		for k1 in k.keys():
			k2 = k[k1]
			if k1 in r.keys():
				j[k2] = r[k1]
				j[k2]
			else:
				if k2 == 'local_queue':
					j[k2] = ''
				else:
					j[k2] = 0
	else:
		print " getjobsummary error: No such request: %s" % workflow
		sys.exit(1)
	
	conn  =  httplib.HTTPSConnection('cmsweb.cern.ch', cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
	r1=conn.request('GET','/reqmgr/reqMgr/outputDatasetsByRequestName?requestName=' + workflow)
	r2=conn.getresponse()
	data = r2.read()
	s = json.loads(data)
	conn.close()
	ods = s
        if len(ods)==0:
                print "No Outpudatasets for this workflow: "+workflow

	duration = timeev*expectedevents/3600
	return {'filtereff':filtereff,'type':type,'status':status,'expectedevents':expectedevents,'inputdataset':inputdataset,'primaryds':primaryds,'prepid':prepid,'timeev':timeev,'priority':priority,'sites':sites,'custodialt1':custodialt1,'zone':getzonebyt1(custodialt1),'js':j,'ods':ods,'duration':duration,'team':team}

def getoverview():
	c = 0
	sys.stdout.flush()
	while c < 3:
		try:
			print "Getting overview... ",
			conn  =  httplib.HTTPSConnection(reqmgrsocket, cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
			r1=conn.request("GET",'/reqmgr/monitorSvc/requestmonitor')
			r2=conn.getresponse()
			print r2.status, r2.reason
			if r2.status == 500:
				c = c + 1
			else:
				c = 100
			s = json.loads(r2.read())
			conn.close()
		except :
			print "Cannot get overview [1]" 
			sys.exit(1)
	if s:
		return s
	else:
		print "Cannot get overview [2]"
		sys.exit(1)

def getRequestsByTypeStatus(typelist,status):
	global overview
	r = []
	for i in overview:
		t = ''
		if 'type' in i.keys():
			t = i['type']
		if 'status' in i.keys():
			st = i['status']
		if t in typelist and st in status:
			r.append(i['request_name'])
	return r
	
def getPhEDExRequestInfo(datasetName):
	info = {}
        url='https://cmsweb.cern.ch/phedex/datasvc/json/prod/RequestList?dataset=' + datasetName
	try:
        	result = json.load(urllib.urlopen(url))
	except:
		print "Cannot get subscription status from PhEDEx"
		return None

	try:
		r = result['phedex']['request']
	except:
		return None
	for i in range(0,len(r)):
        	approval = r[i]['approval']
        	requested_by = r[i]['requested_by']
		custodialsite = r[i]['node'][0]['name']
		id = r[i]['id']
		if 'T1_' in custodialsite:
			info['custodialsite'] = custodialsite
			info['requested_by'] = requested_by
			info['approval'] = approval
			info['id'] = id
			return info
	return None
			
def getPhEDExTransferInfo(datasetName):
	info = {}
	url = 'https://cmsweb.cern.ch/phedex/datasvc/json/prod/subscriptions?dataset=' + datasetName
	try:
        	result = json.load(urllib.urlopen(url))
	except:
		print "Cannot get transfer status from PhEDEx"
		return None
	try:
		r = result['phedex']['dataset'][0]['subscription']
	except:
		return None
	for i in  r:
		node = i['node']
		custodial = i['custodial']
		if 'T1_' in node and custodial == 'y': 
			if i['move'] == 'n':
				type = 'Replica'
			else:
				type = 'Move'
			info['node'] = node
			info['perc'] = int(float(i['percent_bytes']))
			info['type'] = type
			return info
	return None

def getdsdetail(dataset):

	[e,st] = dbs_get_data(dataset)
	if e == -1:
		return [0,'']
	else:
		return [e,st]

def dbs_get_data(dataset):
	output=os.popen("/afs/cern.ch/user/s/spinoso/public/dbssql --input='find sum(block.numevents),dataset.status where dataset="+dataset+"'"+ "|grep '[0-9]\{1,\}'").read()
	ret = output.split(' ')
	ret[0] = int(ret[0])
	ret[1] = ret[1].rstrip()
	return ret

def main():
	global overview,count,jobcount

	overview = getoverview()

	listtype = ['MonteCarlo']
	listtype = ['MonteCarlo','MonteCarloFromGEN']
	liststatus = ['acquired','running']
	liststatus = ['acquired']
	list = getRequestsByTypeStatus(listtype,liststatus)
	#list = list[1:10]

	reqinfo = {}

	print
	print "Number of workflows in %s: %s" % (liststatus, len(list))
	count = 1
	for workflow in list:
		print "%s/%s Get workflow: %s" % (count,len(list),workflow)
		reqinfo[workflow] = getWorkflowInfo(workflow)
		for i in reqinfo[workflow].keys():
			print "\t%s: %s" % (i,reqinfo[workflow][i])
		print
		count = count + 1
	print

	print "| *Overall CPUHours acquired (group by team and zone)* |||||||||"
	team = []
	for i in reqinfo.keys():
		if reqinfo[i]['team'] != []:
			for j in reqinfo[i]['team']:
				if not j in team:
					team.append(j)
	summary = {}
	for t in team:
		summary[t] = {}
		durationacq = getDurationByZoneTeam(reqinfo,'acquired',t)
		for z in durationacq.keys():
			summary[t][z] = durationacq[z]

	zones = durationacq.keys()
	zones.sort()
	allteams = {}
	s = "|*TEAM*           |"
	for i in range(0,len(zones)):
		z = zones[i]
		s = s + "  %10s |" % ('*'+z+'*')
	print s
	for t in summary.keys():
		s = "|%-15s  |" % t 
		for i in range(0,len(zones)):
			z = zones[i]
			s = s + " %10s  |" % (summary[t][z])
			if z in allteams.keys():
				allteams[z] += summary[t][z]
			else:
				allteams[z] = summary[t][z]
		print s

	s = "|*TOTAL*          |"
	for i in range(0,len(zones)):
		z = zones[i]
		s = s + ("  %10s |" % ('*%s*' % allteams[z]) )
	print s
		
	
        sys.exit(0)

if __name__ == "__main__":
        main()
