import re
import sorter
from guessit import guess_file_info

def initSettings(sets):
  sets.address='localhost'
  sets.port=9091
  sets.user=None
  sets.password=None
  sets.timeout=None
  sets.policy = sets.accept
  
  sets.chains.append(Video) 
  #sets.chains.append(OverStuff) 

  global settings
  settings = sets

settings = None
downloadDir = '/home/vfrc2/Downloads'

#Video filter
def Video(torrent, args):
  global settings
  
  res = guess_file_info(torrent.name)
  
  args['chain'].append("Video")
  
  if not ('mimetype' in res.keys() and res['mimetype'].startswith('video')):
    files = torrent.files()
    for fl in files:
      res2 = guess_file_info(files[fl]['name'])
      if not ('mimetype' in res2.keys() and res2['mimetype'].startswith('video')):
        return 
  
  return SeriesFunc(torrent, args) or MovieFunc(torrent, args)
    
    

def SeriesFunc(torrent, args):
  global settings
  
  res = guess_file_info(torrent.name)
  if res['type'] != 'episode':
      files = torrent.files()
      for fl in files:
        res = guess_file_info(files[fl]['name'])
        if res['type'] == 'episode':
          break
      
      args['chain'].append("Series") 
      return

  args['chain'].append("Series") 
  
  args['downloadDir']  =downloadDir+ "/Series/"+res['series']
  
  return settings.accept(torrent,args)

def MovieFunc(torrent, args):
  global settings
  
  res = guess_file_info(torrent.name)
  if res['type'] != 'movie':
    args['chain'].append("Movie")  
    return
    
  args['chain'].append("Movie") 
  
  args['downloadDir'] = downloadDir+ "/Movies/"
  
  return settings.accept(torrent,args)
  
  
  
  

