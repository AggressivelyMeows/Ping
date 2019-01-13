from sanic import Blueprint, response
from server import jinja, db

import aiofiles # very important for asnyc

import random
import os

image_api = Blueprint('image')

@image_api.route('/api/v1/avatar')
async def get_user_avatar(request):
  user = db.users.find_one({'userID': int(request.args['userID'][0])})
  try:
    return await response.file_stream('users/avatars/{}.png'.format(request.args['userID'][0]))
  except:
    # file not found 
    return await response.file_stream('users/default_avatars/{}.png'.format(user['default_avatar']))
  
@image_api.route('/api/v1/default_avatar')
async def get_user_avatar(request):
  id = request.args.get('id')
  if id:
    return await response.file_stream('users/default_avatars/{}.png'.format(id))
  else:
    f_name = random.choice([f.split('.')[0] for f in os.listdir('users/default_avatars/')])
    return await response.file_stream('users/default_avatars/{}.png'.format(f_name))
    