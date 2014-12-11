#!/usr/bin/python
import transmissionrpc
import sorterOptions
import re
import argparse
import fnmatch
import json
import os.path

#Data base for seen id in torrent session
#log file
#

#Group
# -i <id>[,<id>] -select torrents by id
# -n <name> -select torrents by hash (using simple * or ?)
# --all - select all unseened torrents

# -g - group torrent [default]
# -c - clear torrent cooment  seened mark
#


args = None #cli commands
tc=None #transmission client

class settings:
  address='localhost'
  port=9091
  user=None
  password=None
  timeout=None
  
  seenedDbFile=".seened"

  chains = [] #user filter chains
  policy = "skip" #"accept" #if not match any filters
  accept = None
  drop = None
  skip = None
  
cur_sets = None

def main():
  
  global cur_sets
  global tc
  global args
  
  try:
    
    args = parseArgs()
    
    debugMessage("Start programm")
    
    cur_sets = settings()
    
    cur_sets.accept = accept
    cur_sets.drop = drop
    cur_sets.skip = skip
    cur_sets.policy = skip
    
    sorterOptions.initSettings(cur_sets)
    
    loadSeenedDb()
    
    debugMessage("Connecting to  "+str(cur_sets.address)+":"+ str(cur_sets.port))

    tc = transmissionrpc.Client(
      address= cur_sets.address,
      port= cur_sets.port,
      user= cur_sets.user,
      password= cur_sets.password,
      timeout= cur_sets.timeout)
    
    torrents = []
    
    if args.all:
      debugMessage("Get all torrents")
      torrents = getAllTorrents(args.clear)
    else:
      debugMessage("Get torrents with id = "+ str(args.index)+ " or name = "+ str(args.name)+ " or hash = "+ str(args.hash))
      torrents = getTorrents(tid=args.index, name=args.name, thash=args.hash)
    
    if torrents == None:
      print "No torrent"
      torrents = []
      
    debugMessage("total "+str(len(torrents)))
    
    if torrents == None or len(torrents) < 1:
      print "Not new torrents"
      return
    
    if args.clear:
      clearTorrents(torrents)
    else:
      proceedTorrents(torrents)
    
    saveSeenedDb()
  except Exception, err:
    print "Error: ",err
  
  
  
  return

def getAllTorrents(forceAll=False):
  return [t for t in tc.get_torrents() if forceAll or not isSeenedTorrent(t) ]
  
def getTorrents(tid=None, name=None, thash=None):
  tors = getAllTorrents()
  if tors == None:
    tors=[]
  return[t for t in tors if str(t.id) == str(tid) or t.hashString == thash or matchName(t.name,name) ]

seenedDb = []

def loadSeenedDb():
  global seenedDb
  global cur_sets
  if not os.path.exists(cur_sets.seenedDbFile):
    json.dump([], open(cur_sets.seenedDbFile, 'w+'))

  seenedDb = json.load(open(cur_sets.seenedDbFile))
  return
  
def saveSeenedDb():
  global seenedDb
  global cur_sets
  json.dump(seenedDb, open(cur_sets.seenedDbFile, 'w+'))
  

def isSeenedTorrent(torrent):
  global seenedDb
  return torrent.id in seenedDb

def setSeenedTorrent(torrent, isSeened):
  
  if (isSeened and not isSeenedTorrent(torrent)):
    if (not args.dry_run):
      seenedDb.append(torrent.id)
  elif not isSeened and isSeenedTorrent(torrent):
    if (not args.dry_run):
      seenedDb.remove(torrent.id)   
  return
  
def clearTorrents(torrents):
  debugMessage("Clearing seened torrent")
  for t in torrents:
    debugMessage(t.name) 
    try:     
      setSeenedTorrent(t, False)
    except Exception, err:
      print "Error with torrent \'",t.name,"\':",err
  
  return
  
def proceedTorrents(torrents):  
  
  global cur_sets
  
  for tor in torrents:
    try:
      in_put(tor)
    except Exception, err:
      print "Error with torrent \'",tor.name,"\':",err
  
  return

def matchName(name, tname):
  if name == None or tname == None:
    return False
  return fnmatch.fnmatch(name,tname)

def in_put(torrent):
  
  global cur_sets
  
  for chain in cur_sets.chains:
    arg = {}
    arg['chain'] = ['input']
    arg['_action'] = "skip"
    arg['params'] = {}
    arg['downloadDir'] = None

    res = chain(torrent, arg)
    
    if res == None:
      skip(torrent,arg)
      
    if res:
      printChainInfo(torrent,arg)
      printTorrentInfo(torrent)
      return
    elif args.dry_run: #-d 
      printChainInfo(torrent,arg)
  
  arg = {}
  arg['chain'] = ['input policy']    
  cur_sets.policy(torrent, arg) 
  printChainInfo(torrent, arg)
  printTorrentInfo(torrent)

def debugMessage(message):
  global args
  if args.verbose:
    print(message)

def accept(torrent,handlerArgs):
  global args
  
  handlerArgs['_action'] = "accept"
  
  if 'downloadDir' in handlerArgs and handlerArgs['downloadDir'] != None and torrent.downloadDir != handlerArgs['downloadDir']:
    
    debugMessage("Moving torrent to "+ handlerArgs['downloadDir']) 
    
    if (not args.dry_run):
      res = tc.move_torrent_data(torrent.id, handlerArgs['downloadDir'])
      debugMessage(res)
  
  if 'params' in handlerArgs and len(handlerArgs['params']) > 0:
    debugMessage("Setting atributes: ")
    if (not args.dry_run):
      tc.change_torrent(torrent.id,**handlerArgs['params'])
  
  setSeenedTorrent(torrent, True)
  
  torrent.update()
  return True

def drop(torrent,args):
  args['_action'] = "drop"
  if (not args.dry_run):
      tc.remove_torrent(torrent.id)
  return True

def skip(torrent, args):
  args['_action'] = "skip"
  #print "skip by ",args['chain'][-1], 
  return False

def isFilesContains(torrent, funcSearch):
  
  files = torrent.files()
  
  for fl in files:
      if funcSearch(files[fl]['name']) != None:
        return True

  return False 

def printChainInfo(torrent,arg):
   print torrent.name, "\t",arg['_action'],"by", arg['chain'][-1]

def printTorrentInfo(torrent):
  global args
  if args.verbose:
    print "Id : \'"+ str(torrent.id)+"\'"
    print "Download dir: ", torrent.downloadDir  
    print ""

def parseArgs():
  
  #torrent-sorter [-v] [-i|-n|-h|--all] [-n]

  parser = argparse.ArgumentParser(description='reorganize torrents in transmission',
    prog='torrent-sorter')
  
  #debug
  parser.add_argument('-v', '--verbose', action='store_true', 
    help='verbose mode', default = False)
  parser.add_argument('-d', '--dry_run', action='store_true', 
    help='dry run do not modify any params', default = False)  
  
  #select
  parser.add_argument('-i', '--index',
    help='select torrent(s) by id')
  parser.add_argument('-n', '--name',
    help='select torrent(s) by name')
  parser.add_argument('-s', '--hash',
    help='select torrent(s) by hash')
  parser.add_argument('--all', action='store_true',
    help='select all torrents')
  
  #actions
  parser.add_argument('-g', '--group', action='store_true', 
    help='scan and group torrents', default = True) 
  
  parser.add_argument('-c', '--clear', action='store_true', 
    help='clear torrent seen sign from comment', default = False)  
  args = parser.parse_args()
  
  return args


if __name__ == "__main__":
  main();

