from sanic import Blueprint, response
from server import jinja, db, doc, CONFIG
from utils import require_auth, require_role
from datetime import datetime
from shutil import rmtree
import subprocess
import threading
import aiofiles
import logging
import asyncio
import string
import random
import os

render_logger = logging.getLogger('ping.render')
watch_logger = logging.getLogger('ping.watch')
admin_logger = logging.getLogger('ping.admin')

loop = asyncio.get_event_loop()

video_api = Blueprint('video')

# Heres where things get intresting
# 

NORMAL_RESOLUTIONS = {
  '1080p': (1920, 1080),
  '720p': (1280, 720),
  '480p':( 640, 480),
  '360p': (640,360)
}

# TODO: MAKE A RENDER SERVER
# TO HANDLE THE ENCODING OF FILES

@video_api.route('/watch/<videoID>')
@doc.summary("Watch a video")
@jinja.template('video/watch.html')
async def watch_video(request, videoID):
  video = db.videos.find_one({'videoID': videoID})
  
  author = db.users.find_one({'userID': video['author']})
  
  watch_logger.info('{0.ip}:{0.port} has started watching video: {1}'.format(request, video['videoID']))
  
  return {'video': video, 'author': author, 'no_padding': True}

@video_api.route('/api/v1/video/<videoID>/<resolution>_<ts_number>.ts')
@doc.summary("Serve the segmented H264 files")
async def serve_ts_file(request, videoID, resolution, ts_number):
  """
  Ill be honest, i dont know enough
  about HLS to understand why it picked this
  route to get files from but /shurg
  """
  try:
    return await response.file_stream('users/videos/{}/{}_files/{}_{}.ts'.format(
      videoID, resolution, resolution, ts_number))
  except:
    return response.text('No ts file with that name was found', status=404)
  
@video_api.route('/api/v1/video/<videoID>/get_m3u8')
@doc.summary("Serve the actual manifest file to the client")
async def get_m3u8(request, videoID):
  try:
    return await response.file_stream('users/videos/{}/{}.m3u8'.format(videoID,
                                                                      request.args['reso'][0]))
  except FileNotFoundError:
    return response.text('No m3u8 file was found',status=404)

@video_api.route('/api/v1/video/<videoID>/thumbnail')
@doc.summary("Serve the thumbnail for a video")
async def get_thumbnail(request, videoID):
  try:
    return await response.file_stream('users/videos/{}/thumbnail.png'.format(videoID))
  except:
    watch_logger.error('Video thumbnail missing - video: {}'.format(videoID))
    pass
  
@video_api.route('/api/v1/video/<videoID>/get_hls')
@doc.summary("Serve the overal list of resolutions and bitrates for Video JS to set the quality")
async def get_hls_stream(request, videoID):
  
  video = db.videos.find_one({'videoID': videoID})
  
  M3U8_TEXT = '#EXTM3U\n'
  M3U8_TEXT += '#EXT-X-VERSION:3\n'
  for reso_name, resolution in video['resolutions'].items():
    if resolution['encoded'] or 1:
      sizes = resolution['size']
      bandwidth = '800000'
      if reso_name == '480p':
        bandwidth = '1400000'
      elif reso_name == '720p':
        bandwidth = '2800000'
      elif reso_name == 'source':
        bandwidth = '5000000'
      M3U8_TEXT += '#EXT-X-STREAM-INF:BANDWIDTH={},RESOLUTION={}x{}\n'.format(bandwidth,
                                                                              sizes[0],
                                                                              sizes[1])

      M3U8_TEXT += '/api/v1/video/{}/get_m3u8?reso={}\n'.format(video['videoID'], reso_name)
      
  return response.text(M3U8_TEXT)

@video_api.route('/videos/upload')
@jinja.template('video/upload.html')
async def upload_video(request):
  if not require_auth(request):
    return response.redirect('/login?goto=dashboard')
  
  if not CONFIG['allow_uploads']:
    return {'error': 'Sorry. We are not accepting any new uploads right now! If you are the owner of this site, you may set this in your config file'}

  # user is logged in, lets calc some permissions
  if request['session']['user']['role'] == 'owner':
    return {} # owner has full permissions no matter what 
  
  if request['session']['user']['permissions']['allow_upload']:
    return {}
  
  return {}

@video_api.route('/api/v1/video/upload_video', methods=['POST'])
async def handle_upload(request):
  if request.method == 'POST':
    if not request['session'].get('token'):
      return response.redirect('/login')
    
    video_details = request.form
    characters = [x for x in (string.ascii_uppercase + string.ascii_lowercase)]
    videoID = ''.join([random.choice(characters) for _ in range(0,9)])
    
    video = request.files['video'][0]
    thumbnail = request.files['thumbnail'][0]
    save_location = 'users/videos/{}/original.{}'.format(videoID,
                                                     video.type.split('/')[-1])
    thumb_location = 'users/videos/{}/thumbnail.{}'.format(videoID,
                                                           thumbnail.type.split('/')[-1])    
    
    
    try:
      os.mkdir('users/videos/{}/'.format(videoID))
    except FileExistsError:
      pass
    async with aiofiles.open(save_location, mode='wb') as f:
        await f.write(video.body)
    async with aiofiles.open(thumb_location, mode='wb') as f:
        await f.write(thumbnail.body)    
        
    # ok now we check the file and see our options for resolutions
    to_do = "ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 {}".format(save_location)
    
    process = subprocess.Popen(to_do.split(), stdout=subprocess.PIPE)
    
    
    out, err = process.communicate()
    out = out.decode("utf-8") 
    fmt = out.split('x')
    width = int(fmt[0])
    height = int(fmt[1].split('\\')[-1])
    
    resolutions = {'source': {'size': (width, height),
                              'encoded':False}}
    
    aspect_ratio = width / height
    
    for reso_name, reso in NORMAL_RESOLUTIONS.items():
      # check if source is bigger than the format
      # work out the aspect ratio height from this width point
      
      new_height = reso[1] / aspect_ratio
      
      if height > new_height:
        # ok so the source is bigger than this resolution
        # lets add this to the dict of potential resolutions to scale down
        # too
        
        resolutions[reso_name] = {'size': (reso[0], reso[1]),
                                     'encoded':False}
    admin_logger.info('User {} has started uploading video {} with resolutions: {}'.format(request['session']['user']['userID'],
                                                                                           videoID,
                                                                                           ', '.join([k for k, v in resolutions.items()])))
    video_data = {
      'videoID': videoID,
      'title': video_details['title'][0],
      'description': video_details['description'][0],
      'resolutions': resolutions,
      'status':video_details['status'][0],
      'original_format':video.type.split('/')[-1],
      'author': request['session']['user']['userID'],
      'created_at': datetime.utcnow().timestamp(),
      'views': []
    }
    db.videos.insert_one(video_data)
    
    #encode_video(video_data, 'source')
    
    threading.Thread(target=process_video, args=(video_data,)).start()
    return response.redirect('/watch/{}'.format(videoID))
    
@video_api.route('/api/v1/video/<videoID>/delete')
async def delete_video(request, videoID):
  if not require_auth(request):
    return response.redirect('/login')
  
  video = db.videos.find_one({'videoID': videoID})
  userID = request['session']['user']['userID']
  
  if video['author'] != userID or require_role('admin', request['session']['user']):
    # user can delete video!
    db.videos.remove({'videoID': videoID})
    rmtree('users/videos/{}'.format(videoID))
    admin_logger.warning('User {} has deleted video {}'.format(userID, 
                                                               videoID))
    return response.redirect('/dashboard')
  else:
    return response.redirect('/login')
    
# Everything below is talking about how to sort the input video and 
# convert them into the streamable formats
# HLS (m3u8) is going to be how we do this.
    
def process_video(video):
  # in this function, we need to start the process of
  # taking a video and reformatting it to be a streaming
  # format
  # then we have to convert the file into the resolution
  # then we have to split the resolution into its .ts and .m3u8 files
  
  # my god, im truely sorry for this mess right here
  # theres not much else i can do other than to just process it right here
  # a thing to do in the future however could be to move rendering off site
  # maybe onto its own server or program
  # could be an intresting feature
  convert_to_h264(video)
  
  for reso_name, reso in video['resolutions'].items():
    
    # ok now we start to format the videos  
    threading.Thread(None, target=encode_video, args=(video, reso_name)).start()
    
  
def convert_to_h264(video):
  """
  Take a random video format and convert it
  to H264 for further processing
  """
  input = 'users/videos/{}/original.{}'.format(video['videoID'], 
                                            video['original_format'])
  
  output = 'users/videos/{}/source.mp4'.format(video['videoID'])
  to_do = "ffmpeg -i {} -f mp4 -vcodec libx264 -preset fast -profile:v main -strict -2 -acodec aac {} -hide_banner".format(input,
                                                                                                               output)
  
  os.system(to_do)
  render_logger.info('Successfully re-rendered video: {} into H264 encoded video'.format(video['videoID']))

    
def encode_video(video, reso_name):
  """
  Take an input MP4
  and convert it to a .ts folder + .m3u8
  in the resolutions listed
  
  --
  DESIGNED TO BE RUN IN A THREAD!!
  """
  # some important locations of videos
  # and where they go
  sizes = video['resolutions'][reso_name]['size']
  directory = 'users/videos/{}'.format(video['videoID'])
  input = 'users/videos/{}/source.mp4'.format(video['videoID'])
  output = 'users/videos/{}/{}.mp4'.format(video['videoID'],
                                           reso_name)
  # ok so new plan
  # thanks to some more research on this#
  # this site combines both of my plans together
  # https://docs.peer5.com/guides/production-ready-hls-vod/
  # its a long ffmpeg string BUT
  # it will work,, maybe. Who knows.
  # seems this is for an older version of FFMPEG
  # welp
  todo = 'ffmpeg -i {}'.format(input)
  todo += ' -vf scale=w={}:h={}:force_original_aspect_ratio=decrease'.format(sizes[0], sizes[1])
  todo += ' -strict -2 -c:a aac -ar 48000 -b:a 196k -c:v {} -profile:v main -crf 20 -g 48 -keyint_min 48'.format(CONFIG.get('rendering',{}).get('use_codec', 'h264'))
  todo += ' -sc_threshold 0 -b:v 2500k -maxrate 2675k -bufsize 3750k -hls_time 4 -hls_list_size 0'
  todo += ' -hls_segment_filename {1}/{0}_files/{0}_%03d.ts {1}/{0}.m3u8'.format(reso_name,
                                                                                directory)
  
  # ok so now that we have a video in that format, we need to split it into .m3u8 files
  # ffmpeg -i foo.mp4 -codec copy -vbsf h264_mp4toannexb -map 0 -f segment -segment_list out.m3u8 -segment_time 10 out%03d.ts
  # now we need to create the .TS file locations
  try:
    os.mkdir('{}/{}_files'.format(directory, reso_name))
  except FileExistsError:
    pass
  
  render_logger.info('Starting render of video: {} with resolution: {}'.format(video['videoID'],
                                                                               reso_name))
  # ok so, update:
  # seems our friend, ffmpeg, is messing up the aspect ratios in its automagic detection.
  # lets give it some help and just feed it some standard height widths
  #stdout=subprocess.DEVNULL
  ret = subprocess.check_call(todo.split(), stderr=subprocess.STDOUT)
  print(ret)
  
  #os.system(todo)
  
  fixed_resolutions = video['resolutions'][reso_name]['encoded'] = True
  
  db.videos.update_one({'videoID': video['videoID']}, {'$set': {'resolutions': video['resolutions']}})
  
  