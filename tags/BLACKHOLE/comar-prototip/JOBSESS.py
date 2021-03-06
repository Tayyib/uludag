#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2004, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.

# JOBSESS.py
# OB/CALL/EXEC SESSION PROVIDER.

# standart python modules
import os
import sys
import select
import copy
import cPickle
import gdbm

# COMAR modules
import comar_global
import CHLDHELPER, RPCData, SESSION
import TACALL

COMARAPI = None
OM_MGR = None

class jobSessProvider:
	def __init__(self, sessMgr = None, conn = None, user = None, caller = None, key = None):
		global api_propGet, api_propSet, api_method, OM_MGR
		self.mode = ""
		self.user = user
		self.conn = conn
		self.jobkey = key
		self.TTSID = ""
		self.callType = ""
		self.callData = {}
		self.TARPC = None
		self.procHelper	= sessMgr
		self.TIDS = 0
		self.status = "UNKNOWN"
		self.TTSID = ""
		self.subTTSctr = ""
		self.caller = caller
		self.callStack = []
		self.run_que = []
		self.control = ""
		self.runCmdPid = 0
		#self.procHelper.cmdHandler = self.cmdProcessor
		#self.procHelper.addSessionCommand(['TRSU_RTA', # TAM->JOB RegisterTA
		#									'TRSU_RTA', # CALL->JOB RegisterTA
		#									'TNTU_STP', # TAM->JOB StartTA (Processing)
		#									'TRSU_FIN', # CALL->JOB FinishResult
		#									'TNSU_GSID', # CALL->JOB GetLocalTTSID
		#									'TNTU_RDY', # TAM->JOB ResultReady
		#									'TNTU_ERR', # TAM->JOB ResponseIsNone
		#									'TNSU_GET', # CALL->JOB GetValue
		#									'LNSU_KILL', # TAM->ALL KillSelf
		#									'IRTU_GTD', # TAM->ANY GetTASessionData
		#									'IRTU_PID']) # TAM->ANY GetUniquePID
		#CSL = "method test (x=5, y=15) { test = x+y; }"
		#print "Try Register CSL:"
		#print OM_MGR.addOMCode(node = "COMAR:test.node.x",
		#		       IID = "NEWIID", code = CSL,
		#		       fileName="test.csl", scriptType="CSL")

	def register(self, rpc = None):
		global OM_MGR
		if rpc.Type == "OMCALL":
			node = rpc["name"]			
			omtype = OM_MGR.getOMNodeType(node)
			if omtype[1] == "INVALID":
				print "JSP: Invalid call:", node, omtype
				return 1
		self.TARPC = rpc
		self.TTSID  = rpc.TTSID
		self.status = "NEW"
		# We save our callData for resume/reload..

		print "Job Session Driver: New TA JOB Session registered:", os.getpid(), "PID:", self.procHelper.myPID, "PARENT:", self.procHelper.gloPPid
		#ci = EXEC.callerInfoObject()
		# Collect CallerInfo..
		print "REGISTER TA USER INFO", os.getpid(), self.user
		print "REGISTER TA CONN INFO", os.getpid(), self.conn
		print "REGISTER TA JOB INFO ", os.getpid(), self.jobkey
		#callerInfo = callerInfoObject()
		#callerInfo.TAData = self
		print "REGISTER TA JOB CINFO ", os.getpid()
		return 0

	def reload(self, conn = None, user = None, caller = None, key = None):
		# WE fill our job instance data:
		self.user		= user
		self.conn		= conn
		self.jobkey		= key
		self.caller		= caller

	def startTransaction(self, tainf):
		# This is a main loop.
		# We must create call session childs.
		global OM_MGR
		self.procHelper.useDBSocket()
		OM_MGR.setDBHelper(self.procHelper)
		c_prms = self.TARPC.getPropertyMulti(propName = "parameter",  all=1)
		c_name = self.TARPC["name"]
		c_type = self.TARPC["type"]
		c_model = self.TARPC.Type
		c_obj = None
		c_code = None
		if c_model == "OBJCALL":
			print self.TARPC.xml
			c_obj = self.TARPC["object"]
		elif c_model == "EXEC":
			c_code = self.TARPC["code"]
			
		self.procHelper.addSessionCommand(["TRSU_OMC", "TRSU_OBJC","TRSU_TAE", "TRSU_RTA", "TRSU_FIN", "TNSU_GET", "TNSU_GSID", "TRSU_SOBJ", "LNTU_KILL" ])
		self.procHelper.cmdHandler = self.sessionCmdHandler
		self.procHelper.debug = 255
		#self.procHelper.sendParentCommand(cmd = "INSU_YTT", pid = self.procHelper.myPID, tid = 0, data=None)
		#self.procHelper.dumpInfo()
		#runCmd Proto: callModel, callType, callName, callPrms, callObj, callCode, caller="UI", wait_pid = 0, setvalue=None
		root = self.runCmd(c_model, c_type, c_name, c_prms, c_obj, c_code, "UI", 0)

		print "RunCmd Returned..", self.procHelper.myPID
		self.callStack.append( (root, c_model, c_type, c_name, c_prms, c_obj, c_code) )
		self.procHelper.sendCommand(root, "TRTU_RUN", root, 0, "1")
		#self.procHelper.dumpInfo()
		self.procHelper.debug = 0 #255
		while 1:
			tmp = self.procHelper.ReadFDs
			#print "\n\n", os.getpid(), "STA LOOP LISTEN:"
			#self.procHelper.dumpListener()
			ret = self.procHelper.ProcessIO()
			#print "STA LOOP", ret, self.runCmdPid, os.getpid(), self.procHelper.modName
			if ret == -2:
				#self.procHelper.exit()
				#select.select([], [], [], 5)
				print self.procHelper.modName, "STA LOOP EXITED:", os.getpid()
				break
		return

	def runCmd(self, callModel, callType, callName, callPrms, callObj, callCode, caller="UI", wait_pid = 0, setvalue=None):
		print "\n\nJOBSESS:145 Start Transaction:", self.procHelper.modName, self.procHelper.myPID, "\n\n"
		chldPID = self.procHelper.makeChild()
		parentrpid = os.getpid()
		self.TIDS += 1
		seq_key = str(self.TIDS)
		pid = os.fork()
		self.runCmdPid = os.getpid()
		if pid:
			self.procHelper.setIODebug(chldPID, 0, self.procHelper.modName + "->jobSessProvider")
			self.procHelper.initForParent(chldPID)
			self.procHelper.debug = 0
			#self.procHelper.registerChild(chldPID, self.procHelper.myPID)

			print self.procHelper.myPID, "run Cmd...", chldPID, self.procHelper.chlds
			self.callData[chldPID] = [ callModel, callType, callName, callPrms, callObj, callCode, wait_pid ]
			self.control = "parent"
			return chldPID
		else:
			# Child..
			# Job session only create a CALL Session and pass
			# required parameters.

			self.procHelper.setIODebug(chldPID, 0, "jobSessProvider->" + self.procHelper.modName)
			gloPIO = self.procHelper.PID2io(chldPID)
			gloPPid = self.procHelper.myPID + 0
			#gloPIO, gloPPid, PID
			new_ph = CHLDHELPER.childHelper(gloPIO, gloPPid, chldPID, "jobSessProvider->" + self.procHelper.modName)
			new_ph.initForChild(gloPPid)
			new_ph.parentppid = parentrpid
			new_ph.useDBSocket()
			self.control = "child"
			#new_ph.initForChild(gloPPid)
			print "Call Session Start With pids: ", os.getpid(), chldPID, new_ph.parentppid, new_ph.myPID, new_ph.gloPPid
			self.procHelper = new_ph
			self.procHelper.clearSessionCommands()
			self.procHelper.addSessionCommand(["TRSU_OMC", "TRSU_OBJC", "TRTU_RUN", 
						"TRSU_TAE", "TRSU_RTA", "TRSU_FIN", "TNSU_GET", "TNSU_GSID", "LNTU_KILL", "TRSU_SOBJ", "LNTU_KILL" ])
			self.procHelper.cmdHandler = self.sessionCmdChildHandler
			prmArray = callPrms
			OM_MGR.setDBHelper(self.procHelper)
			TACALL.COMARAPI = COMARAPI
			TACALL.OM_MGR = OM_MGR

			callSession = TACALL.TAcallSession(sessMgr = new_ph,
									seq_key = seq_key,
									parent_seq = "0",
									Type = callType,
									Name = callName,
									prms = prmArray,
									conn = self.conn,
									user = self.user,
									caller = caller)
			if callModel == "OMCALL":
				callSession.initOMCALL(callName)
			elif callModel == "OBJCALL":
				callSession.initOBJCALL(callObj, callName)
			self.run_que.append(callSession)
			self.procHelper.minChild = 0
			while 1:
				ret = self.procHelper.ProcessIO()				
				print "STA LOOP 200", ret, self.runCmdPid, "pidof:", os.getpid(), "getppid:", os.getppid(), self.procHelper.modName
				#print SESSION.stackImage()
				if ret == -2:
					#self.procHelper.exit()
					#select.select([], [], [], 5)
					print self.procHelper.modName, "STA LOOP EXITED:", os.getpid()
					break
				elif type(ret) == type( () ):	# A Command Return...
					command = ret[0]
					print self.procHelper.modName, "STA LOOP COMMAND:", os.getpid(), command

			new_ph.exit()
	passTRTUN = 0
	def sessionCmdChildHandler(self, From, srcpid, ppid, rfd, pkPid, pkTid, command, pkData):
		print "JOBSESS Line 214: A Session From Children Cmd:", self.control, self.runCmdPid, os.getpid(), From, srcpid, ppid, rfd, pkPid, pkTid, command
		if command == "TRSU_FIN":
			print self.procHelper.myPID,self.procHelper.modName, "child execute resulted:", pkPid, srcpid, "->", self.callData[srcpid]
			if self.callData[srcpid][6]:
				print "Result for child send to:", self.callData[srcpid][6]
				self.procHelper.sendCommand(self.callData[srcpid][6], "TRTU_TAE", self.callData[srcpid][6], pkTid, str(pkData))
				del self.callData[srcpid]
			else:
				#first call...
				self.procHelper.sendParentCommand("TRSU_TAE", self.procHelper.myPID, 0, str(pkData))
				
		elif command == "TRTU_RUN":
			# This is a child mode
			print self.control, self.procHelper.myPID,self.procHelper.modName, "CALL SESSION CHILD EXECUTE START"
			if len(self.run_que):
				cs = self.run_que.pop(0)
				retval = cs.execute()
				print os.getppid(), self.procHelper.myPID,self.procHelper.modName, self.control, "CALL SESSION CHILD EXECUTE RETURNED", retval				
				self.procHelper.sendParentCommand("TRSU_FIN", self.procHelper.myPID, 0, retval)				
				while 1:
					if self.procHelper.waitForParentCmd(timeout = 2):
						break

			cmd = self.procHelper.getParentCommand()
			print os.getpid(), "After TRTU_RUN:", cmd
			if cmd[2] == "LNTU_KILL":
				# wait for childs..
				#self.procHelper.waitchilds()
				self.procHelper.exit()

		elif command == "TRSU_OMC":
			# This is a parent mode..
			print self.control, self.procHelper.myPID,self.procHelper.modName, "New OM Execute call reached.. From:", pkPid, srcpid, self.callData[srcpid]
			rpc = RPCData.RPCStruct()
			rpc.fromString(pkData)
			print "New OMEXEC Call:", rpc.xml
			c_prms = rpc.getPropertyMulti(propName = "parameter",  all=1)
			c_name = rpc["name"]
			c_type = rpc["type"]
			c_model = rpc.Type
			c_obj = None
			c_code = None
			if c_model == "OBJCALL":
				c_obj = rpc["object"]
			elif c_model == "EXEC":
				c_code = rpc["code"]
			#self.procHelper.sendParentCommand(cmd = "INSU_YTT", pid = self.procHelper.myPID, tid = 0, data=None)
			#self.procHelper.dumpInfo()
			#self.callData[chldPID] = [ callModel, callType, callName, callPrms, callObj, callCode ]
			
			caller = self.callData[srcpid][2]
			root = self.runCmd(c_model, c_type, c_name, c_prms, c_obj, c_code, caller, pkPid)
			print "RunCmd Returned..", self.procHelper.myPID
			self.procHelper.sendCommand(root, "TRTU_RUN", root, 0, "1")

			#def runCmd(self, callModel, callType, callName, callPrms, callObj, callCode):
		elif command == "TRSU_OBJC":
			# This is a parent mode..
			print self.control, self.procHelper.myPID,self.procHelper.modName, "New OBJ call reached.. From:", pkPid, srcpid, self.callData[srcpid]
			rpc = RPCData.RPCStruct()
			rpc.fromString(pkData)
			print "New OBJEXEC Call:", rpc.xml
			c_prms = rpc.getPropertyMulti(propName = "parameter",  all=1)
			c_name = rpc["name"]
			c_type = rpc["type"]
			c_model = rpc.Type
			c_obj = None
			c_code = None
			if c_model == "OBJCALL":
				c_obj = rpc["object"]
			elif c_model == "EXEC":
				c_code = rpc["code"]
			#self.procHelper.sendParentCommand(cmd = "INSU_YTT", pid = self.procHelper.myPID, tid = 0, data=None)
			#self.procHelper.dumpInfo()
			#self.callData[chldPID] = [ callModel, callType, callName, callPrms, callObj, callCode ]
			print "OBJC CallData", self.callData
			caller = self.callData[srcpid][2]
			root = self.runCmd(c_model, c_type, c_name, c_prms, c_obj, c_code, caller, pkPid)
			print "RunCmd Returned..", self.procHelper.myPID
			self.procHelper.sendCommand(root, "TRTU_RUN", root, 0, "1")
			#def runCmd(self, callModel, callType, callName, callPrms, callObj, callCode):

	def sessionCmdHandler(self, From, srcpid, ppid, rfd, pkPid, pkTid, command, pkData):
		print "JOBSESS Line 300: A Session Cmd:", self.control, self.runCmdPid, os.getpid(), From, srcpid, ppid, rfd, pkPid, pkTid, command #, pkData
		cmdque = [ (srcpid, pkPid, pkTid, command, pkData) ]		
		while len(cmdque):
			srcpid, pkPid, pkTid, command, pkData = cmdque.pop()
			if command == "TRSU_FIN":
				print self.procHelper.myPID,self.procHelper.modName, "execute resulted:", pkPid, srcpid #, "->", self.callData[srcpid]
				if self.callData[srcpid][6]:
					print "Result send to:", self.callData[srcpid][6]
					self.procHelper.sendCommand(self.callData[srcpid][6], "TRTU_TAE", self.callData[srcpid][6], pkTid, str(pkData))
					self.procHelper.sendCommand(srcpid, "LNTU_KILL", srcpid, pkTid, None)
					self.procHelper.wait_pid(int(srcpid))
					del self.callData[srcpid]
				else:
					#first call... Our Parent is main.. 
					print "END OF TA:", str(pkData), "from:", self.procHelper.myPID,"to ->", self.procHelper.gloPPid					
					self.procHelper.sendCommand(int(srcpid), "LNTU_KILL", srcpid, pkTid, None)
					self.procHelper.sendParentCommand("TRSU_TAE", self.procHelper.myPID, 0, str(pkData))
					while 1:
						x =  self.procHelper.wait_pid(int(srcpid))
						if x == 2:
							cmd = self.procHelper.getParentCommand()
							if cmd:
								print "REACHED TA COMMAND AFTER TRSU_TAE", cmd
								cmdque.append(self.procHelper.gloPPid, int(cmd[0]), int(cmd[1]), cmd[2], cmd[3])
						else:
							break
			elif command == "LNTU_KILL":
				print self.procHelper.myPID, os.getpid(), "LNTU_KILL Arrived :("
				#self.procHelper.waitchilds()
				self.procHelper.exit()
			elif command == "TRTU_RUN":
				# This is a child mode
				print self.control, self.procHelper.myPID,self.procHelper.modName, "CALL SESSION EXECUTE START"
				if len(self.run_que):
					cs = self.run_que.pop(0)
					retval = cs.execute()
					print os.getppid(), self.procHelper.myPID,self.procHelper.modName, self.control, "CALL SESSION EXECUTE RETURNED" #, retval
					self.procHelper.sendParentCommand("TRSU_FIN", self.procHelper.myPID, 0, retval)
	
					#self.procHelper.exit()
	
			elif command == "TRSU_OMC" or command == "TRSU_OBJC":
				# This is a parent mode..
				#print self.control, self.procHelper.myPID,self.procHelper.modName, "New OM Execute call reached.. From:", pkPid, srcpid, self.callData[srcpid]
				rpc = RPCData.RPCStruct()
				rpc.fromString(pkData)
				#print "New OMEXEC/OBJCALL Call:", rpc.xml
				c_prms = rpc.getPropertyMulti(propName = "parameter",  all=1)
				c_name = rpc["name"]
				c_type = rpc["type"]
				c_model = rpc.Type
				c_obj = None
				c_code = None
				if c_model == "OBJCALL":
					c_obj = rpc["object"]
				elif c_model == "EXEC":
					c_code = rpc["code"]
				#self.procHelper.sendParentCommand(cmd = "INSU_YTT", pid = self.procHelper.myPID, tid = 0, data=None)
				#self.procHelper.dumpInfo()
				#self.callData[chldPID] = [ callModel, callType, callName, callPrms, callObj, callCode ]
				print "CALLDATA FOR TA:", srcpid, self.callData
				caller = self.callData[srcpid][2]
				root = self.runCmd(c_model, c_type, c_name, c_prms, c_obj, c_code, caller, pkPid)
				print "RunCmd Returned..", self.procHelper.myPID
				self.procHelper.sendCommand(root, "TRTU_RUN", root, 0, "1")
	
				#def runCmd(self, callModel, callType, callName, callPrms, callObj, callCode):
			elif command == "TRSU_SOBJ":
				#print "JOBSESS 321: A Object Register Command:", pkData
				self.procHelper.sendParentCommand(command, pkPid, pkTid, pkData)
			elif command == "TRSU_CALL":
				print "JOBSESS 324: A New Call Command:", pkData
			

	def processOMCall(self):
		pass
