from redbot.core import commands
import requests
import asyncio
from bs4 import BeautifulSoup
import os
import ast
import time
import discord
import datetime
import redbot.core.data_manager
import re

global isRunning
isRunning = False
global inSession
inSession = False
global headers
headers = False
global cog_path
cog_path = ""
global stopTime
stopTime = 0
global recDict
recDict = False
global queueDict
queueDict = False
global tempDict
tempDict = False
global lbDict
lbDict = {}
global lbRegDict
lbRegDict = {}
global queueProc
queueProc = False
global lastID
lastID = False
global channel
channel = None
global activeQueue
activeQueue = []
global queueTime
queueTime = False
global locked
locked = False
global current
global current2
current, current2 = False, False
global numeralmatch
numeralmatch = re.compile(r'(?i)[-_ ](?=[MDCLXVI]+\b)(M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))$')
global delayTime
delayTime = 60
global regionWhiteList
regionWhiteList = []


class Scroll(commands.Cog):
	"""NS Manual Recruitment Helper."""

	def __init__(self, bot):
		global bot1
		self.bot = bot
		bot1 = self.bot
	async def CheckPath(self, ctx, param: str):
		#checks if a certain file exists in the cog's directory; returns true/false and a filepath for i/o purposes
		global cog_path
		global bot1
		if cog_path == "":
			cog_path = str(redbot.core.data_manager.cog_data_path())
		if not(os.path.exists(os.path.join(cog_path, "scroll"))):
			os.makedirs(os.path.join(cog_path, "scroll"))
		filepath = os.path.abspath(os.path.join(cog_path, "scroll", param))
		return(filepath, os.path.isfile(filepath))
	async def FirstRun(self, ctx):
		#this one just spits out some initial stuff from the backlog so there's no processing delay.
		global recDict
		global lbDict
		global queueDict
		global delayTime
		#the dict of active recruiters and backlog are both keyed by the region that's being recruited/backlogged for for convenience
		#here we're just seeing if there's enough for a full bucket, spitting it out if so, and sending a boilerplate if not
		for key in recDict:
			if len(queueDict[key][0]) >= 8:
				natList = queueDict[key][0][-8:]
				for a in queueDict[key]:
					del a[-8:]
				buttonView = discord.ui.View()
				item = discord.ui.Button(style=discord.ButtonStyle.gray, label=str(recDict[key][0][1]), url="https://www.nationstates.net/page=compose_telegram?tgto={recipients}&message={message}".format(recipients = str(natList)[1:-1].replace("'","").replace(" ",""), message = recDict[key][0][2].replace("%","%25")))
				buttonView.add_item(item=item)
				await ctx.send(f"A new batch of nations has been founded; please follow the provided button and press \"Send\".\n\n__**TARGETS:**__\n<@{recDict[key][0][0]}>\n`{str(natList)[1:-1]}`", view = buttonView)
				queuePath = await self.CheckPath(ctx, "queueDict.txt")
				with open(queuePath[0], "w") as f:
					f.write(str(queueDict))
				#since this is the always the run of an active session there's only one person recruiting, so only the first person in the recruitment dict needs to get updated
				lbDict[recDict[key][0][0]][0] += 8
				lbPath = await self.CheckPath(ctx, "leaderboards.txt")
				with open(lbPath[0], "w") as f:
					f.write(str(lbDict))
				lbRegPath = await self.CheckPath(ctx, "regionboards.txt")
				lbRegDict[key][recDict[key][0][0]][0] += 8
				with open(lbRegPath[0], "w") as f:
					f.write(str(lbRegDict))
			else:
				await ctx.send("Not enough nations could be found, please wait a moment.")
		await asyncio.sleep(delayTime)
		await self.ActiveLoop(ctx)
	async def ActiveLoop(self, ctx):
		#we do a ping for new nations every (50-250)s, as determined by the user
		global inSession
		global current3
		global delayTime
		#this is scuffed as fuck, but it's logging so i can immediately cancel that task if a session ends via everyone leaving/forcestop
		current3 = asyncio.current_task()
		while inSession == True:
			await self.ActivePing(ctx)
			await asyncio.sleep(delayTime)
	async def ActivePing(self, ctx):
		#we ping for new nations every time the loop above runs :)
		global queueDict
		global recDict
		global lastID
		global headers
		global lbDict
		global lastTime
		global activeQueue
		global current4
		global regionWhiteList
		#once again logging for session end/forcestop purposes
		current4 = asyncio.current_task()
		#grabbing every new found since the last time a similar ping was made
		#since it's required to start background pings before launching an active session, there will *always* be an event ID on file.
		#as currently stands this also won't catch everything if there's over 100 founds in the 50-250s window, but that's an exceedingly extreme edge case and that kinda founding spike would probably fuck NS itself up as well lmaoo
		req = requests.get(f"https://www.nationstates.net/cgi-bin/api.cgi?q=happenings;filter=founding;sinceid={lastID}", headers = headers)
		#pulling lists of the important stuff out
		eventlist = BeautifulSoup(req.text, "lxml-xml").find_all("EVENT")
		timeslist = BeautifulSoup(req.text, "lxml-xml").find_all("TIMESTAMP")
		regionTextlist = BeautifulSoup(req.text, "lxml-xml").find_all("TEXT")
		regionlist = []
		for text in regionTextlist:
			regionlist.append(str(text).split("%%")[1])
		#if at least one founding has happened in the last window ('cause otherwise we'd crash lmao)
		if len(eventlist) > 0:
			lastID = eventlist[0].get('id')
			for count,a in enumerate(range(len(eventlist))):
				b = str(eventlist[a]).split("@@")[1]
				#if there's a roman numeral at the end, or an arabic number period, we run a check for if the nation can accept recruitment TGs (with a 0.7s timer to make sure we don't run afoul of api limits)
				#if it passes both checks, it gets yeeted onto the list of usable stuff
				#TODO: change all the print() stuff to output to a log file or something instead lmao
				if not(any(char.isdigit() for char in str(b))) and not(re.search(numeralmatch, b)) and not(regionlist[count] in regionWhiteList):
					await asyncio.sleep(0.7)
					req2 = requests.get(f"https://www.nationstates.net/cgi-bin/api.cgi?nation={b}&q=tgcanrecruit", headers = headers)
					if '1' in req2.text:
						activeQueue.append([b, eventlist[a].get('id'), int(timeslist[a].string)])
						print(f"{b} : yes")
					else:
						print(f"{b} : nonrecruitable")
				else:
					print(f"{b} : numbers")
		else:
			activeQueue = []
		#we add all the usable stuff to both the default backlog queue, and the backlog for each registered region
		for a in activeQueue:
			queueDict['DEFAULT'][0].append(a[0])
			queueDict['DEFAULT'][1].append(a[1])
			queueDict['DEFAULT'][2].append(a[2])
		for key in recDict:
			numRecruiters = len(recDict[key])
			for a in activeQueue:
				queueDict[key][0].append(a[0])
				queueDict[key][1].append(a[1])
				queueDict[key][2].append(a[2])
				temp1 = []
				temp2 = []
				temp3 = []
				for b in range(len(queueDict[key][0])):
					if not(queueDict[key][0][b] in temp1):
						temp1.append(queueDict[key][0][b])
						temp2.append(queueDict[key][1][b])
						temp3.append(queueDict[key][2][b])
				queueDict[key][0] = temp1
				queueDict[key][1] = temp2
				queueDict[key][2] = temp3
			for key2 in queueDict:
				if not(key2 in recDict):
					for a in activeQueue:
						queueDict[key2][0].append(a[0])
						queueDict[key2][1].append(a[1])
						queueDict[key2][2].append(a[2])
						temp1 = []
						temp2 = []
						temp3 = []
						for b in range(len(queueDict[key2][0])):
							if not(queueDict[key2][0][b] in temp1):
								temp1.append(queueDict[key2][0][b])
								temp2.append(queueDict[key2][1][b])
								temp3.append(queueDict[key2][2][b])
						queueDict[key2][0] = temp1
						queueDict[key2][1] = temp2
						queueDict[key2][2] = temp3
			#if there's enough fresh nations in the queue to give a full set of 8 to every person currently recruiting
			#we chop off the relevant bits 
			if (len(queueDict[key][0]) >= numRecruiters * 8):
				tempQueue = [queueDict[key][0][-(numRecruiters * 8):],queueDict[key][1][-(numRecruiters * 8):],queueDict[key][2][-(numRecruiters * 8):]]
				queueDict[key] = [queueDict[key][0][:-(numRecruiters * 8)],queueDict[key][1][:-(numRecruiters * 8)],queueDict[key][2][:-(numRecruiters * 8)]]
				sendList = []
				#constructing a list w/ the sender and a set of 8 sendees
				for a in recDict[key]:
					sendList.append([a, []])
				for a in range(len(tempQueue[0])):
					sendList[a%numRecruiters][1].append(tempQueue[0][a])
				print(f"[{datetime.datetime.fromtimestamp(time.time()).strftime('%H:%M:%S')}] {str(sendList)}")
				#we use the list to make a url button for each sender
				#formatted [[[uid1,display name 1,template string1],[list of nations]],[[uid2 [...]
				#it's kinda ass but it works lmao
				buttonView = discord.ui.View()
				pingString = ""
				for a in sendList:
					item = discord.ui.Button(style=discord.ButtonStyle.gray, label=str(a[0][1]), url="https://www.nationstates.net/page=compose_telegram?tgto={recipients}&message={message}".format(recipients = str(a[1])[1:-1].replace("'","").replace(" ",""), message = a[0][2].replace("%","%25")))
					buttonView.add_item(item=item)
					pingString += f"<@{a[0][0]}> \n`{str(a[1])[1:-1]}`\n"
					lbDict[a[0][0]][0] += len(a[1])
					lbRegDict[key][a[0][0]][0] += len(a[1])
				lastTime[key] = time.time()
				#and we send out the message with a ping to everyone active recruiting!
				await ctx.send(f"A new batch of nations has been founded; please follow the provided button and press \"Send\".\n\n__**TARGETS:**__\n{pingString[:-1]}", view=buttonView)
			#if a full set of 8 per recruiter *hasn't* been filled yet, and more than five minutes have passed since the last such message
			#being able to send *something* feels better than not giving the user any feedback at all, thus
			elif (time.time() - lastTime[key] >= 300):
				#if it can send every active recruiter at least one nation, we do the same dealio as above
				#constructing a list of senders and their sendees, and evenly distributing as best as possible
				if (len(queueDict[key][0]) >= numRecruiters):
					tempQueue = [queueDict[key][0],queueDict[key][1],queueDict[key][2]]
					queueDict[key] = [[],[],[]]
					sendList = []
					for a in recDict[key]:
						sendList.append([a, []])
					for a in range(len(tempQueue[0])):
						sendList[a%numRecruiters][1].append(tempQueue[0][a])
					print(f"[{datetime.datetime.fromtimestamp(time.time()).strftime('%H:%M:%S')}] {str(sendList)}")
					#once again setting up buttons, and sending out
					buttonView = discord.ui.View()
					pingString = ""
					for a in sendList:
						item = discord.ui.Button(style=discord.ButtonStyle.gray, label=str(a[0][1]), url="https://www.nationstates.net/page=compose_telegram?tgto={recipients}&message={message}".format(recipients = str(a[1])[1:-1].replace("'","").replace(" ",""), message = a[0][2].replace("%","%25")))
						buttonView.add_item(item=item)
						pingString += f"<@{a[0][0]}> \n`{str(a[1])[1:-1]}`\n"
						lbDict[a[0][0]][0] += len(a[1])
						lbRegDict[key][a[0][0]][0] += len(a[1])
					lastTime[key] = time.time()
					await ctx.send(f"A new batch of nations has been founded; please follow the provided button and press \"Send\".\n\n__**TARGETS:**__\n{pingString[:-1]}", view = buttonView)
				else:
					#if there's not enough to give everyone at least one nation, we set the cap timer a bit shorter and send a message so there's at least some feedback as to what's going on
					await ctx.send(f"not enough new nations have spawned to distribute to `{key}`, please wait a little longer.")
					lastTime[key] = time.time() - 180
		activeQueue = []
		#and we write updated leaderboard and queue information to their external files regardless of what happens so ideally that stuff doesn't get lost in a bot crash
		lbPath = await self.CheckPath(ctx, "leaderboards.txt")
		with open(lbPath[0], "w") as f:
			f.write(str(lbDict))
		lbRegPath = await self.CheckPath(ctx, "regionboards.txt")
		with open(lbRegPath[0], "w") as f:
			f.write(str(lbRegDict))
		queuePath = await self.CheckPath(ctx, "queueDict.txt")
		with open(queuePath[0], "w") as f:
			f.write(str(queueDict))
			
		#TODO: add new queue stuff into queues of regions not currently recruiting
	@commands.group(name="rec")
	@commands.bot_in_a_guild()
	async def rec(self, ctx):
		"""Starts or stops an active recruitment session."""
		
	@rec.command(name="start")
	async def start(self, ctx, templatenumber: str):
		"""Registers you for the current recruitment session, and starts a session if there isn't one running."""
		#this is the actual-ass user-side start command :')
		global tempDict
		global recDict
		global inSession
		global headers
		global queueProc
		global stopTime
		global channel
		global souplist2
		global lastTime
		global isRunning
		global lbDict
		global queueDict
		global current
		global current2
		global delayTime
		author = ctx.author
		lbPath = await self.CheckPath(ctx, "leaderboards.txt")
		lbRegPath = await self.CheckPath(ctx, "regionboards.txt")
		if headers == False:
			#we want a user agent for doing API stuff, so this block checks if there's one currently set or externally stored, and tells the user to set one if not
			agentPath = await self.CheckPath(ctx, "uagent.cfg")
			if agentPath[1] == False:
				await ctx.send(f"{author.mention}:\nERROR: No valid User-Agent has been set; please set one with >setagent")
				return
			else:
				with open(agentPath[0], 'r') as f:
					agent = str(f.readline())
			headers = {"User-Agent": f"Scroll manual recruitment cog for Discord's RedBot (developer:valkynora@gmail.com; current instance run by: {agent})"}
		tempPath = await self.CheckPath(ctx, "tempDict.txt")
		if queueProc == True:
			#if background backlog population is *currently* in the middle of a ping, it'll tell the user to wait to avoid stuff fucking up (tm)
			await ctx.send(f"{author.mention}:\nQueue population is currently ongoing, please wait a moment before starting.")
			return
		if isRunning == False:
			#if background backlog isn't running *at all*, it'll direct the user to start that, 'cause it's important :))
			await ctx.send(f"{author.mention}:\nBackground Queue is not currently running; please enable it with >queuestart")
			return
		if tempDict == False:
			#we check if the bot has template data here or externally, and if not, direct the user to create a new template
			if tempPath[1] == False:
				await ctx.send(f"{author.mention}:\nNo template data has been found. Please add a template with >template add.")
				return
			else:
				with open(tempPath[0], 'r') as f:
					readtemp = f.readline()
				try:
					#if the external template data can't be read as a dict for some reason, it'll wipe what remains and direct the user to add new stuff
					tempDict = ast.literal_eval(readtemp)
				except:
					await ctx.send(f"{author.mention}:\nERROR: Template data is corrupted; deleting. Please add a new template with >template add.")
					os.remove(tempPath[0])
					return
		if not(str(author.id) in tempDict):
			#if the user doesn't have any registered templates, make a new one smdh
			await ctx.send(f"{author.mention}:\nNo template registered to you has been found. Please add a template with >template add.")
			return
		try:
			#we check if the given template number actually correlates with one the user has registered
			#and if so, grab the template string and the region it's associated with to add to the recruiter dictionary later
			tempString = tempDict[str(author.id)][int(templatenumber)-1][0]
			tempRegion = tempDict[str(author.id)][int(templatenumber)-1][1]
		except:
			await ctx.send(f"{author.mention}:\nNo template with that number has been found. Please check that you have selected the correct number with >template list")
			return
		if inSession == False:
			#if there's no active recruiting session, we check if the previous session ended long enough ago
			#register the stuff just above to the recruitment dictionary, and start a session
			if ((time.time() - stopTime) < (delayTime+10)):
				await ctx.send(f"{author.mention}:\nPrevious recruitment session halted too recently; please wait a couple seconds and try again.")
				return
			recDict = {tempRegion: [[str(author.id),str(author.display_name),tempString]]}
			channel = ctx.channel.id
			souplist2 = []
			await ctx.send(f"{author.mention} is now recruiting using template `{tempString}`.")
			inSession = True
			#resetting the "haven't sent a message in x seconds" timer
			lastTime = {tempRegion: time.time()}
			#checkin' if leaderboard data exists in some capacity, and creating a blank setup if there isn't or it's unreadable
			if lbDict == {}:
				if lbPath[1] == True:
					with open(lbPath[0], 'r') as f:
						readtemp = f.readline()
					try:
						lbDict = ast.literal_eval(readtemp)
					except:
						await ctx.send(f"{ctx.author.id}:\nERROR: Leaderboard data is corrupted; deleting the leaderboard file.")
						os.remove(lbPath[0])
			if not(str(author.id) in lbDict):
				lbDict[str(author.id)] = [0, str(author.display_name)]
			#doin' the same thing for regional leaderboards:
			if lbRegDict == {}:
				if lbRegPath == True:
					with open(lbRegPath[0], 'r') as f:
						readtemp = f.readline()
					try:
						lbRegDict = ast.literal_eval(readtemp)
					except:
						await ctx.send(f"{ctx.author.id}:\nERROR: Regional Leaderboard data is corrupted; deleting the file.")
							os.remove(lbRegPath[0])
			if not(str(author.id) in lbRegDict[tempRegion]):
				lbRegDict[tempRegion][str(author.id)] = [0, str(author.display_name)]
			#we yeet the tasks for background population at the start of a session, and restart them after
			#to make sure it doesn't do that while a session's active. this is a) for API reasons, and b) everything founded in that timeframe gets added anyway (once the TODO a bit further up gets addressed lmao)
			current.cancel()
			current2.cancel()
			current, current2 = False, False
			#and now we run the special function that immediately gives nations because wait time was complained about :')
			await self.FirstRun(ctx)
		else:
			#if there's already an active session running, we do checks for if it's in a different channel/if the user's already recruiting
			#and add them to the session if not
			for key in recDict:
				for a in recDict[key]:
					if str(author.id) in a:
						await ctx.send(f"{author.mention}:\nYou are currently already recruiting.")
						return
			if not(ctx.channel.id == channel):
				await ctx.send(f"{author.mention}:\nRecruitment is already ongoing in a different channel or server.")
			else:
				if not(str(author.id) in lbDict):
					lbDict[str(author.id)] = [0, str(author.display_name)]
				if not(str(author.id) in lbRegDict[tempRegion]):
					lbRegDict[tempRegion][str(author.id)] = [0, str(author.display_name)]
				if tempRegion in recDict:
					recDict[tempRegion].append([str(author.id),str(author.display_name),tempString])
					await ctx.send(f"{author.mention} is now recruiting using template `{tempString}`.")
				else:
					recDict[tempRegion] = [[str(author.id),str(author.display_name),tempString]]
					await ctx.send(f"{author.mention} is now recruiting using template `{tempString}`.")
					lastTime[tempRegion] = time.time()
					
	@rec.command(name="stop")
	async def stop(self, ctx):
		"""Removes yourself from the current recruitment session."""
		#the actuall-ass user-side command for removing yourself from a session :)
		global headers
		global inSession
		global recDict
		global stopTime
		global activeQueue
		global lastTime
		global lbDict
		global current3
		global current4
		global queueDict
		global queueProc
		author = ctx.author
		if headers == False:
			#technically i'm not sure we even need a UAgent check here since nothing it does induces further api calls, but better safe than sorry i guess?
			agentPath = await self.CheckPath(ctx, "uagent.cfg")
			if agentPath[1] == False:
				await ctx.send(f"{author.mention}:\nERROR: No valid User-Agent has been set; please set one with >setagent")
				return
			else:
				with open(agentPath[0], 'r') as f:
					agent = str(f.readline())
			headers = {"User-Agent": f"Scroll manual recruitment cog for Discord's RedBot (developer:valkynora@gmail.com; current instance run by: {agent})"}
		if inSession == False:
			#obviously do nothing if there's no active session in the first place
			await ctx.send(f"{author.mention}:\nNo recruitment session is currently running.")
			return
		#if there is though, we check through the dict of active recruiters to see if the user who triggered the command is present
		#if not we yell at 'em
		#if yes we remove 'em
		b = 0
		for key in recDict:
			templist = []
			for a in recDict[key]:
				if not(a[0] == str(author.id)):
					templist.append(a)
				else:
					b = key
			recDict[key] = templist
		if b == 0:
			await ctx.send(f"{author.mention}:\nYou are not currently recruiting.")	
		else:
			#we write leaderboards/backlock externally again just in case
			lbPath = await self.CheckPath(ctx, "leaderboards.txt")
			with open(lbPath[0], "w") as f:
				f.write(str(lbDict))
			queuePath = await self.CheckPath(ctx, "queueDict.txt")
			with open(queuePath[0], 'w') as f:
				f.write(str(queueDict))
			#if the removal if this user means there's no more recruiters for a region, it removes that region from actively sending messages
			#and if it means there' sno more recruiters period, it stops recruitment
			if len(recDict[b]) == 0:
				lastTime.pop(b)
				recDict.pop(b)
				if len(recDict) == 0:
					recDict = False
					inSession = False
					lastTime = False
					activeQueue = []
					stopTime = time.time()
					await ctx.send(f"{author.mention}:\nThe current recruiting session has now ended.")
					lbPath = await self.CheckPath(ctx, "leaderboards.txt")
					with open(lbPath[0], "w") as f:
						f.write(str(lbDict))
					print(lbPath[0])
					#we yeet the tasks for the active session loop/ping, just in case
					try:
						current3.cancel()
					except:
						pass
					try:
						current4.cancel()
					except:
						pass
					#and restart background population
					if (current == False) and (current2 == False):
						isRunning = True
						queueProc = False
						await self.PassiveLoop(ctx)
					return
			
			await ctx.send(f"{author.mention}:\nYou have been removed from the current recruiting session.")
					
	@commands.command()
	async def forcestop(self, ctx):
		"""Forcibly stops the current recruitment session."""
		#in case someone's gotten pulled away and is deep behind, or if something fucks up somehow
		#TODO (maybe:) a command to stop just a single other user for the former use case?
		global headers
		global inSession
		global recDict
		global stopTime
		global activeQueue
		global lastTime
		global lbDict
		global current3
		global current4
		global queueDict
		global queueProc
		if not(headers):
			#once again i don't actually think a UAgent check is necessary, but it doesn't hurt i guess
			agentPath = await self.CheckPath(ctx, "uagent.cfg")
			if agentPath[1] == False:
				await ctx.send(f"{ctx.author.mention}:\nNo valid User-Agent has been found. Please set one with >setagent")
				return
			else:
				with open(agentPath[0], 'r') as f:
					headers = {"User-Agent": f"Scroll manual recruitment cog for Discord's RedBot (developer:valkynora@gmail.com; current instance run by: {str(f.readline())})"}
		#we reset a bunch of variables, write leaderboards/backlog externally in case
		#and yeet the tasks for active loop/ping // restarts the background one
		stopTime = time.time()
		inSession = False
		recDict = False
		lastTime = {}
		activeQueue = []
		lbPath = await self.CheckPath(ctx, "leaderboards.txt")
		with open(lbPath[0], "w") as f:
			f.write(str(lbDict))
		queuePath = await self.CheckPath(ctx, "queueDict.txt")
		with open(queuePath[0], 'w') as f:
			f.write(str(queueDict))
		print(lbPath[0])
		await ctx.send(f"{ctx.author.mention}:\nStopped all recruitment.")
		try:
			current3.cancel()
		except:
			pass
		try:
			current4.cancel()
		except:
			pass
		if (current == False) and (current2 == False):
			isRunning = True
			queueProc = False
			await self.PassiveLoop(ctx)
		
	async def PassiveLoop(self, ctx):
		#this guy's running in the background to acccumulate stuff for the backlog
		global inSession
		global isRunning
		global queueTime
		global locked
		global current
		current = asyncio.current_task()
		print(current)
		#every half hour, we do a ping for new founds, as seen in the function below
		while isRunning == True:
			queueTime = time.time()
			if not(inSession):
				await self.QueuePing(ctx)
				print(f"[{datetime.datetime.fromtimestamp(time.time()).strftime('%H:%M:%S')}] ping")
			#okay doing this as a for in 1800 rather than a simple sleep(1800) is an artifact of my old shitty way of doing things
			#but i'm not 100% sure stuff wouldn't break if i changed it to that?
			for a in range(1800):
				if isRunning == False:
					break
				await asyncio.sleep(1)
	async def QueuePing(self, ctx):
		#actually doing the gross api stuff :(
		global headers
		global lastID
		global queueDict
		global queueProc
		global current2
		current2 = asyncio.current_task()
		queueProc = True
		print("Queueproc = true")
		#if there isn't a lastID assigned currently (e.g. on first run); check for the stored value
		lastPath = await self.CheckPath(ctx, "lastID.cfg")
		queuePath = await self.CheckPath(ctx, "queueDict.txt")
		if not(lastID):
			#if the bot can't find a lastID on file:
			if lastPath[1] == False:
				#pull 100 as a baseline dealio; set lastID at most recent
				req = requests.get("https://www.nationstates.net/cgi-bin/api.cgi?q=happenings;filter=founding+cte;limit=100", headers=headers)
				eventlist = BeautifulSoup(req.text, "lxml-xml").find_all("EVENT")
				timeslist = BeautifulSoup(req.text, "lxml-xml").find_all("TIMESTAMP")
				regionTextlist = BeautifulSoup(req.text, "lxml-xml").find_all("TEXT")
				regionlist = []
				for text in regionTextlist:
					regionlist.append(str(text).split("%%")[1])
				ctelist = []
				list1 = []
				#api batches come ordered new>old; i want old>new for this
				eventlist.reverse()
				timeslist.reverse()
				for count,a in enumerate(range(len(eventlist))):
					#isolate the nation name
					b = str(eventlist[a]).split("@@")[1]
					if "founded" in str(eventlist[a]).split("@@")[2].split("%%")[0]:
						#check if the happening isn't too old (2d cutoff)
						if not((time.time() - int(timeslist[a].string)) > 172000):
							#basic number filter; do a tgcanrecruit check if there's none
							if not(any(char.isdigit() for char in b)) and not(re.search(numeralmatch, b)) and not(regionlist[count] in regionWhiteList):
								await asyncio.sleep(0.7)
								req2 = requests.get(f"https://www.nationstates.net/cgi-bin/api.cgi?nation={b}&q=tgcanrecruit", headers=headers)
								#if recruiting is available; yeet them into the "good" list along with their id
								if '1' in req2.text:
									print(b)
									list1.append([b, eventlist[a].get('id'), int(timeslist[a].string)])
					else:
						ctelist.append(b)
				#grab the id of the most recent one
				try:
					lastID = eventlist[-1].get('id')
				except:
					pass
				try:
					print(ctelist)
				except:
					pass
				#queueDict is formatted {"region1":[[nation1, nation2, <...>],[eventid1, eventid2, <...>],[timestamp1, timestamp2, <...>],"region2":} etc
				#this just goes through the various regional queues, checks if stuff on the "good" list is already in there, then adds them if they're not.
				for a in list1:
					for key in queueDict:
						if not(a[1] in queueDict[key][1]):
							queueDict[key][0].append(a[0])
							queueDict[key][1].append(a[1])
							queueDict[key][2].append(a[2])
				#writing the most recent ID to file in case of bot reboots
				with open(lastPath[0], "w") as f:
					f.write(lastID)
				#also writing the new queues to file :)
				with open(queuePath[0], "w") as f:
					f.write(str(queueDict))
				queueProc = False
				print("queueProc = false")
				return
			#if there *is* a lastID on file, just yeet it into the variable and continue:
			else:
				with open(lastPath[0], 'r') as f:
					lastID = f.readline()
					print(lastID)
		#the following should run if there's a) a lastID in the backup file, or b) a lastID in program memory
		#pull as many foundings as you can from present to the lastID on record
		req = requests.get(f"https://www.nationstates.net/cgi-bin/api.cgi?q=happenings;filter=founding+cte;limit=100;sinceid={lastID}", headers = headers)
		eventlist = BeautifulSoup(req.text, "lxml-xml").find_all("EVENT")
		timeslist = BeautifulSoup(req.text, "lxml-xml").find_all("TIMESTAMP")
		regionTextlist = BeautifulSoup(req.text, "lxml-xml").find_all("TEXT")
		ctelist = []
		print(len(eventlist))
		#if there's too many to grab with one api request; we'll loop until it returns <100 results; i.e. when we've hit the target id, *OR* when grabbed events are too old to be useful (>2d)
		if len(eventlist) == 100:	
			caughtUp=False
			lastID2 = eventlist[-1].get('id')
			while caughtUp == False:
				await asyncio.sleep(0.7)
				req = requests.get(f"https://www.nationstates.net/cgi-bin/api.cgi?q=happenings;filter=founding+cte;limit=100;sinceid={lastID};beforeid={lastID2}", headers = headers)
				list1 = BeautifulSoup(req.text, "lxml-xml").find_all("EVENT")
				list2 = BeautifulSoup(req.text, "lxml-xml").find_all("TIMESTAMP")
				list3 = BeautifulSoup(req.text, "lxml-xml").find_all("TEXT")
				timeslist.extend(list2)
				eventlist.extend(list1)
				regionTextlist.extend(list3)
				print(len(eventlist))
				if not(len(list1) == 0):
					lastID2 = list1[-1].get('id')
				if (len(list1) < 100) or ((time.time() - int(list2[-1].string)) > 172000) or (len(timeslist) >= 3500):
					caughtUp = True
				print(caughtUp)
		try:
			lastID = eventlist[0].get('id')
		except:
			pass
		with open(lastPath[0], 'w') as f:
			f.write(lastID)
		regionlist = []
		for text in regionTextlist:
			regionlist.append(str(text).split("%%")[1])
		#no need to do any extra else-ing if the list was already <100 length
		#reverse the list so we're reading old->new
		eventlist.reverse()
		timeslist.reverse()
		regionlist.reverse()
		list1 = []
		for count,a in enumerate(range(len(eventlist))):
			#isolate the nation name
			b = str(eventlist[a]).split("@@")[1]
			if "founded" in str(eventlist[a]).split("@@")[2].split("%%")[0]:
				if not(any(char.isdigit() for char in b)) and not(re.search(numeralmatch, b)) and not(regionlist[count] in regionWhiteList):
					await asyncio.sleep(0.7)
					req2 = requests.get(f"https://www.nationstates.net/cgi-bin/api.cgi?nation={b}&q=tgcanrecruit", headers=headers)
					if '1' in req2.text:
						print(b)
						list1.append([b, eventlist[a].get('id'), int(timeslist[a].string)])
			else:
				ctelist.append(b)
		#once again adding stuff from the "good" list to queues as necessary
		print(ctelist)
		for a in list1:
			for key in queueDict:
				if not(a[1] in queueDict[key][1]):
					queueDict[key][0].append(a[0])
					queueDict[key][1].append(a[1])
					queueDict[key][2].append(a[2])
		#culling time :)
		#gonna go through default + regional queues and a) clip off everything longer than 1500, and b) clip off everything beyond that that's >2 days old
		for key in queueDict:
			queueDict[key] = [queueDict[key][0][-1500:],queueDict[key][1][-1500:],queueDict[key][2][-1500:]]
			tempa = []
			tempb = []
			tempc = []
			b = 0
			for a in queueDict[key][0]:
				#grab the ones that aren't too old or on the list of stuff that's CTE'd since; paste back in after
				try:
					if ((time.time() - queueDict[key][2][b]) < 172000): #and (queueDict[key][0][a] not in ctelist):
						tempa.append(queueDict[key][0][b])
						tempb.append(queueDict[key][1][b])
						tempc.append(queueDict[key][2][b])
				except IndexError:
					print(b)
					print(len(queueDict[key][0]), len(queueDict[key][1]), len(queueDict[key][2]))
				b += 1
			queueDict[key] = [tempa, tempb, tempc]
		#and writing the current queue to file
		with open(queuePath[0], "w") as f:
			f.write(str(queueDict))
		queueProc = False
		print("queueProc = false")
		
	@commands.command()
	async def queuestart(self,ctx):
		"""Starts background queue population."""
		#the actual-ass user-side command to accumulate a backlog
		global queueDict
		global queueProc
		global headers
		global isRunning
		global queueTime
		global locked
		queuePath = await self.CheckPath(ctx, "queueDict.txt")
		print(queuePath[0])
		if headers == False:
			#as always we check for a usable UAgent
			agentPath = await self.CheckPath(ctx, "uagent.cfg")
			if agentPath[1] == False:
				await ctx.send(f"{ctx.author.mention}:\nERROR: No valid User-Agent has been set; please set one with >setagent")
				return
			else:
				with open(agentPath[0], 'r') as f:
					agent = str(f.readline())
			headers = {"User-Agent": f"Scroll manual recruitment cog for Discord's RedBot (developer:valkynora@gmail.com; current instance run by: {agent})"}
		if isRunning == False and inSession == False:
			#we check for backlog data, and create a blank setup if not available or unreadable
			if queueDict == False:
				if queuePath[1] == False:
					await ctx.send("No Queue data found; generating some blanks :)")
					queueDict = {"DEFAULT": [[],[],[]]}
					with open(queuePath[0], "w") as f:
						f.write(str(queueDict))
				else:
					with open(queuePath[0], "r") as f:
						readtemp = f.readline()
					try: 
						queueDict = ast.literal_eval(readtemp)
					except:
						await ctx.send("Queue data corrupted, repopulating with a blank queue")
						queueDict = {"DEFAULT": [[],[],[]]}
						with open(queuePath[0], "w") as f:
							f.write(str(queueDict))
			else:
				#then we start the loop that does the pings :)
				isRunning = True
				await ctx.send("Now populating the queue in the background.")
				await self.PassiveLoop(ctx)
		else:
			#if backlog population is already happening (or an active session is running), we don't do the above obviously
			await ctx.send("Queue population is already running.")

	@commands.command()
	async def queuestop(self,ctx):
		"""Stops background queue population."""
		#an actual-ass user-side command for stopping backlog population, though i'm not sure there's an actual good reason for this beyond reloading the cog without potentially fucking stuff up?
		global isRunning
		global current
		global current2
		global queueDict
		if isRunning == True:
			#very basic stuff; we reset some variables and yeet the async tasks for backlog loop/ping
			isRunning = False
			current.cancel()
			current2.cancel()
			current, current2 = False, False
			await ctx.send("Queue population has stopped.")
			queuePath = await self.CheckPath(ctx, "queueDict.txt")
			with open(queuePath[0], 'w') as f:
				f.write(str(queueDict))
		else:
			await ctx.send("Queue population is not currently running.")
		

	@commands.command()
	async def queuesize(self,ctx):
		"""Displays how many recipients are waiting in the backlog for each registered region."""
		#exactly what it says on the tin. no api interaction here
		global queueDict
		global delayTime
		global recDict
		queuePath = await self.CheckPath(ctx, "queueDict.txt")
		if queueDict == False:
			if queuePath[1] == False:
				await ctx.send("No Queue data found; generating some blanks :)")
				queueDict = {"DEFAULT": [[],[],[]]}
				with open(queuePath[0], 'w') as f:
					f.write(str(queueDict))
			else:
				with open(queuePath[0], 'r') as f:
					readtemp = f.readline()
				try:
					queueDict = ast.literal_eval(readtemp)
				except:
					await ctx.send("Queue data corrupted; repopulating with a blank queue.")
					queueDict = {"DEFAULT": [[],[],[]]}
					with open(queuePath[0], 'w') as f:
						f.write(str(queueDict))
		sendString = "```"
		for key in queueDict:
			sendString += f"\n{key}: {str(len(queueDict[key][0]))}"
		sendString += "\n```"
		if recDict:
			sendString = sendString[:-3] + "\nTIME TO COMPLETION:\n"
			for key in recDict:
				sendString += f"{key}: {str(datetime.timedelta(seconds = divmod(len(queueDict[key][0]),(len(recDict[key])*8))[0]*delayTime))}\n"
			sendString += "```"
		await ctx.send(sendString)
	@commands.group(name="template")
	async def template(self, ctx):
		"""Manages the templates registered to you."""
	@template.command(name="add", usage="<%template-id%> <region_url>")
	async def add(self, ctx, *param: str):
		"""Registers a template for use in recruiting."""
		#for >template add, we check if the command's reasonably formed, then register a template to the user.
		#we also check if there's backlog data for the region provided, and create some if no.
		global tempDict
		global queueDict
		tempPath = await self.CheckPath(ctx, "tempDict.txt")
		queuePath = await self.CheckPath(ctx, "queueDict.txt")
		author = ctx.author
		if len(param) < 2:
			await ctx.send(f"{author.mention}:\nERROR: incorrect amount of parameters provided. Too few")
		elif len(param) > 2: 
			await ctx.send(f"{author.mention}:\nERROR: incorrect amount of parameters provided. Too many!")

		else:
			if "region=" in param[1]:
				regionstr = param[1].lower().split("region=")[1].replace('_', ' ')
				template = param[0]
				if tempDict == False:
					#if there's no pre-existing template data, we make a blank set and register :)
					#the same goes for backlog if *that* doesn't exist
					#TODO (maybe): prevent the user from registering the same template id multiple times?
					if tempPath[1] == False:
						tempDict = {str(author.id): [[template, regionstr]]}
						with open(tempPath[0], 'w') as f:
							f.write(str(tempDict))
						await ctx.send(f"{author.mention}:\nTemplate `{template}` has been registered for the region `{regionstr}`.")
						if queueDict == False:
							if queuePath[1] == False:
								queueDict = {"DEFAULT": [[],[],[]]}
								with open(queuePath[0], 'w') as f:
									f.write(str(queueDict))
							else:
								with open(queuePath[0], 'r') as f:
									readtemp = f.readline()
								try:
									queueDict = ast.literal_eval(readtemp)
								except:
									await ctx.send(f"{author.mention}:\nERROR: Queue data has been found corrupted while updating queue settings.")
									queueDict = {"DEFAULT": [[],[],[]], regionstr: [[],[],[]]}
									with open(queuePath[0], 'w') as f:
										f.write(str(queueDict))
									return
						if not(regionstr in queueDict):
							queueDict[regionstr] = queueDict["DEFAULT"]
							with open(queuePath[0], 'w') as f:
								f.write(str(queueDict))
						return
					else:
						with open(tempPath[0], 'r') as f:
							readtemp = f.readline()
						try:
							tempDict = ast.literal_eval(readtemp)
						except:
							await ctx.send(f"{author.mention}:\nERROR: Template data is corrupted; deleting data.\nAdding new template `{template}` for region `{regionstr}`.")
							os.remove(tempPath[0])
							tempDict = {str(author.id): [[template, regionstr]]}
							if queueDict == False:
								if queuePath[1] == False:
									queueDict = {"DEFAULT": [[],[],[]]}
									with open(queuePath[0], 'w') as f:
										f.write(str(queueDict))
								else:
									with open(queuePath[0], 'r') as f:
										readtemp = f.readline()
									try:
										queueDict = ast.literal_eval(readtemp)
									except:
										await ctx.send(f"{author.mention}:\nERROR: Queue data has been found corrupted while updating queue settings.")
										queueDict = {"DEFAULT": [[],[],[]], regionstr: [[],[],[]]}
										with open(queuePath[0], 'w') as f:
											f.write(str(queueDict))
										return
							if not(regionstr in queueDict):
								queueDict[regionstr] = queueDict["DEFAULT"]
								with open(queuePath[0], 'w') as f:
									f.write(str(queueDict))
							return
				if str(author.id) in tempDict:
					#if the author already has templates registered, yeet it onto the list; if not, make a new entry to the dict
					tempDict[str(author.id)].append([template, regionstr])
				else:
					tempDict[str(author.id)] = [[template, regionstr]]
				with open(tempPath[0], 'w') as f:
					f.write(str(tempDict))
				await ctx.send(f"{author.mention}:\nTemplate `{template}` has been registered for the region `{regionstr}`.")
				if queueDict == False:
					#and once again generating a fresh backlog / regional backlog if they don't already exist
					if queuePath[1] == False:
						queueDict = {"DEFAULT": [[],[],[]], regionstr: [[],[],[]]}
						with open(queuePath[0], 'w') as f:
							f.write(str(queueDict))
					else:
						with open(queuePath[0], 'r') as f:
							readtemp = f.readline()
						try:
							queueDict = ast.literal_eval(readtemp)
						except:
							await ctx.send(f"{author.mention}:\nERROR: Queue data has been found corrupted while updating queue settings.")
							queueDict = {"DEFAULT": [[],[],[]], regionstr: [[],[],[]]}
							with open(queuePath[0], 'w') as f:
								f.write(str(queueDict))
							return
				if not(regionstr in queueDict):
					queueDict[regionstr] = queueDict["DEFAULT"]
					with open(queuePath[0], 'w') as f:
						f.write(str(queueDict))
			else:
				await ctx.send(f"{author.mention}: An invalid region URL has been provided.")
	@template.command(name="remove", usage = "<%template-id%>")
	async def remove(self, ctx, template : str):
		"""Removes a template currently registered to you."""
		#we remove a registered template, if the inputted data corresponds to one :)
		global tempDict
		global queueDict
		tempPath = await self.CheckPath(ctx, "tempDict.txt")
		queuePath = await self.CheckPath(ctx, "queueDict.txt")
		author = ctx.author
		if tempDict == False:
			#in hindsight i absolutely could've shoved a lot of this "check if x exists, and if not, create a blank version" into functions of their own 'cause this shit repeats
			#but that's a problem for future devi cleaning up the codebase sometime >.>
			if tempPath[1] == False:
				await ctx.send(f"{author.mention}:\nNo template data found; please register a template with >template add.")
				return
			else:
				with open(tempPath[0], 'r') as f:
					readtemp = f.readline()
				try:
					tempDict = ast.literal_eval(readtemp)
				except:
					await ctx.send(f"{author.mention}:\nERROR: Template data is corrupted; deleting data.")
					os.remove(tempPath[0])
					return
		if str(author.id) in tempDict:
			templist = []
			for a in tempDict[str(author.id)]:
				#technically i also guess this removes all templates registered w/ the same id string, but eh
				if not(template == a[0]):
					templist.append(a)
			if len(templist) == 0:
				#if a user no longer has registered templates, it yeets them from the dictionary :)
				#and if there's no one left in said dictionary, we yeet that too :))
				tempDict.pop(str(author.id))
				if len(tempDict) == 0:
					tempDict = False
					os.remove(tempPath[0])
				else:
					tempDict[str(author.id)] = templist
			else:
				tempDict[str(author.id)] = templist
			with open(tempPath[0], 'w') as f:
				f.write(str(tempDict))
			await ctx.send(f"{author.mention}:\nAll templates matching the given ID have been removed.")
		else:
			await ctx.send(f"{author.mention}:\nThere are currently no templates registered to you.")
	@template.command(name="list")
	async def _list(self, ctx):
		"""Lists the templates currently registered to you."""
			#and finally we list the templates registered to the user
			#once again this messy code block where i check if template data exists >.>
		global tempDict
		global queueDict
		tempPath = await self.CheckPath(ctx, "tempDict.txt")
		queuePath = await self.CheckPath(ctx, "queueDict.txt")
		author = ctx.author
		if tempDict == False:
			if tempPath[1] == False:
				await ctx.send(f"{author.mention}:\nNo template data found; please register a template with >template add.")
				return
			else:
				with open(tempPath[0], 'r') as f:
					readtemp = f.readline()
				try:
					tempDict = ast.literal_eval(readtemp)
				except:
					await ctx.send(f"{author.mention}:\nERROR: Template data is corrupted; deleting data.")
					os.remove(tempPath[0])
					return
		if not(str(author.id) in tempDict):
			await ctx.send(f"{author.mention}:\nThere are currently no templates registered to you.")
		else:
			sendstring = f"{author.mention}:\nThese are the templates currently registered to you:\n```\n"
			num = 1
			for a in tempDict[str(author.id)]:
				sendstring += f"{num}: {a[0]} | {a[1]}\n"
				num += 1
			sendstring += "```"
			await ctx.send(sendstring)
					
	@commands.command()
	async def status(self, ctx):
		"""Shows the current operational status of the Scroll cog."""
		#we literally just print off a bunch of variables from elsewhere
		global isRunning
		global inSession
		global queueProc
		global delayTime
		global recDict
		global queueDict
		sendString = f"```\nPassive Queue Population: {str(isRunning)}\nRecruitment Session Active: {str(inSession)}\nQueue Processing ongoing: {str(queueProc)}\nCurrent batch delay: {delayTime}\n```"
		await ctx.send(sendString)
		
	@commands.command()
	async def setagent(self, ctx, *, agent: str):
		"""Sets the User-Agent for the bot."""
		#exactly what it says on the tin; any command that interacts with the API will check if this is set
		global headers
		agentPath = await self.CheckPath(ctx, "uagent.cfg")
		with open(agentPath[0], 'w') as f:
			f.write(agent)
		headers = {"User-Agent": f"Scroll manual recruitment cog for Discord's RedBot (developer:valkynora@gmail.com; current instance run by: {agent})"}
		await ctx.send(f"User-Agent has been set to {agent}.")
		
	@commands.command()
	async def leaderboards(self, ctx):
		"""Displays the recruitment leaderboards."""
		global lbDict
		lbPath = await self.CheckPath(ctx, "leaderboards.txt")
		#the same kludgey "check if x exists and generate a blank thing if not" dealio you've seen fifty times by now
		#TODO: separate leaderboards per region maybe? but i'd need to rewrite all the leaderboard shit to store per region in addition to overall
		if lbDict == {}:
			if lbPath[1] == False:
				await ctx.send("No leaderboard data has been found; please start recruiting to populate the leaderboards.")
				return
			else:
				with open(lbPath[0], 'r') as f:
					readtemp = f.readline()
				try:
					lbDict = ast.literal_eval(readtemp)
				except:
					await ctx.send(f"{ctx.author.id}:\nERROR: Leaderboard data is corrupted; deleting the leaderboard file.")
					os.remove(lbPath[0])
					return
		totalCount = 0
		for key in lbDict:
			totalCount += lbDict[key][0]
		sendstring = "**__LEADERBOARDS__**\nTotal telegrams sent via Scroll: {str(totalCount)}\n"
		num = 1
		#this abomination sorts a dict by an item in a list associated with each key :))
		#we use this to display a nice ranked list for leaderboard purposes
		for key in {k: v for k, v in sorted(lbDict.items(), key = lambda item: item[1], reverse=True)}:
			sendstring += f"{str(num)}. `{str(lbDict[key][1])}`: {str(lbDict[key][0])}\n"
			num += 1
		await ctx.send(sendstring)
	@leaderboards.command(name="region", usage="<region name>")
	async def region(self, ctx, *, region: str):
		"""Displays the recruitment leaderboards for a specific region."""
		global lbRegDict
		lbRegPath = await self.CheckPath(ctx, "regionboards.txt")
		#we've all seen this a million times :')
		if lbRegDict == {}:
			if lbRegPath[1] == False:
				await ctx.send("No regional leaderboard data has been found, please recruit to populate the leaderboards.")
				return
			else:
				with open(lbRegPath[0], 'r') as f:
					readtemp = f.readline()
				try:
					lbRegDict = ast.literal_eval(readtemp)
				except:
					await ctx.send(f"{ctx.author.id}:\nERROR: Leaderboard data is corrupted; deleting the regional leaderboard file.")
					os.remove(lbRegPath[0])
					return
		if region in lbRegDict:
			totalCount = 0
			for key in lbRegDict[region]:
				totalCount += lbRegDict[region][key][0]
			sendstring = f"**__LEADERBOARDS FOR {region}__**\nTotal telegrams sent via Scroll: {str(totalCount)}\n"
			num = 1
			for key in {k: v for k, v in sorted(lbRegDict[region].items(), key = lambda item: item[1], reverse=True)}:
				sendstring += f"{str(num)}. `{str(lbRegDict[region][key][1])}`: {str(lbRegDict[region][key][0])}\n"
				num += 1
			await ctx.send(sendstring)
		else:
			await ctx.send("No region with that name could be found in leaderboard data.")
	@commands.command()
	async def tgqueue(self, ctx):
		"""Displays the current NS TGAPI Telegram queue."""
		#blame thorn for this existing; i'm not sure anyone else actually uses it lmaoo
		#anyway it (provided a UAgent) grabs the lengths of the NS-side manual/api/stamp queues
		global headers
		if headers == False:
			agentPath = await self.CheckPath(ctx, "uagent.cfg")
			if agentPath[1] == False:
				await ctx.send(f"{ctx.author.mention}:\nERROR: No valid User-Agent has been set; please set one with >setagent")
				return
			else:
				with open(agentPath[0], 'r') as f:
					agent = str(f.readline())
			headers = {"User-Agent": f"Scroll manual recruitment cog for Discord's RedBot (developer:valkynora@gmail.com; current instance run by: {agent})"}
		await asyncio.sleep(1)
		#as always we have an enforced delay before doing a call :))
		queuereq = requests.get("https://www.nationstates.net/cgi-bin/api.cgi?q=tgqueue", headers = headers)
		#technically i guess i could've condensed the next six lines into one, but this is more legible lmao
		soup = BeautifulSoup(queuereq.text, "lxml-xml")
		manual = soup.find("MANUAL").string
		mass = soup.find("MASS").string
		api = soup.find("API").string
		sendstring=f"Current TG Queue:\n```Manual: {manual}\nMass: {mass}\nAPI: {api}```"
		await ctx.send(sendstring)
	@commands.command()
	async def wipequeue(self, ctx, region_name: str):
		"""wipes the saved queue for a given region"""
		#i'm not super sure what the use case here is outside of fixing potential fuckups, but oh well lmao
		global queueDict
		region_name = region_name.replace('_',' ')
		#in hindsight this probably throws an error immediately after launch but i honestly can't be assed to paste in another one of the "check if x exists" blocks *or* fix my code to shunt that shit off into functions
		#so it's a problem for future devi :))))
		if region_name in queueDict:
			queueDict[region_name] = [[],[],[]]
			queuePath = await self.CheckPath(ctx, "queueDict.txt")
			with open(queuePath[0], 'w') as f:
				f.write(str(queueDict))
	@commands.command()
	async def delay(self, ctx, delay: int):
		"""sets the minimum delay for new batches of nations (50-250s)"""
		global delayTime
		try:
			print(int(delay))
			if 50 <= delay <= 250:
				delayTime = delay
				await ctx.send(f"Active Queue delay has been set to `{delayTime}`.")
			else:
				await ctx.send("The provided value is outside of the given range. Please use a whole number between 50 and 250 seconds.")
		except:
			await ctx.send("The value given is not a valid integer. Please input a whole number between 50 and 250")
			
	@commands.command(name="regionwhitelist")
	async def regionWhiteList(self, ctx, *regions):
		"""Designates a list of regions to ignore founds/refounds in."""
		global regionWhiteList
		regionWhiteList = list(regions)
		for a in range(len(regionWhiteList)):
			regionWhiteList[a]=regionWhiteList[a].replace(" ","_")
		await ctx.send(f"{ctx.author.mention}: The following regions will no longer be recruited from: `{str(regionWhiteList)[1:-1]}`")
		print(regionWhiteList)
###lb format {uid: [count, displayname]}
###regional lb format {region: {uid1: [count, displayname], uid2: [count, displayname]}, region2: {uid1: [count, displayname]...}}
###rec format {region: [[uid1, dispname, templatestring1],[uid2, tempstring2]]}