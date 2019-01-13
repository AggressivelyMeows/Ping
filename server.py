"""
An example peice of software that shows that if a 18 year old
junior developer can make a video streaming site in under a week.

Please take everything in here with a grain of salt but if you
do like what you see, feel free to contact me at the email below.
I'm always looking for a job to do!

Obviously, i do not have the raw strength as Google
or facebook or Amazon. But i have tried to make the code
as fast and scalable as possible. 

If you have any ideas, tips, updates or anything. Please
hit me up on Discord: @Cerulean#7014

cerulean.connor@gmail.com - Email
"""

TODO = """
Ceruleans ToDo list:
- add oauth2 support
- Add custom avatar support (Image API)
"""

# Set up basic config here
PORT = 8080
DEFAULT_PERMISSIONS = {
  'allow_upload': False,
  'edit_users':False,
  'edit_videos':False
}

ROLES = {
  'owner': {k:True for k, v in DEFAULT_PERMISSIONS.items()},
  'admin':{k:True for k, v in DEFAULT_PERMISSIONS.items()},
  'author': {
    'allow_upload':True,
    'edit_own_videos':True,
    'edit_own_posts':True,
    'allow_comment':True,
    'rank': 2
  },
  'viewer': {
    'allow_comment':True,
    'allow_upload':True,
    'rank': 3
  }
}
ROLES['owner']['rank'] = 0
ROLES['admin']['rank'] = 1
import logging

logger = logging.getLogger('ping')
logger.setLevel(logging.DEBUG)
if not logger.handlers:
  # create file handler which logs even debug messages
  fh = logging.FileHandler('ping.log')
  fh.setLevel(logging.DEBUG)
  # create console handler with a higher log level
  ch = logging.StreamHandler()
  ch.setLevel(logging.ERROR)
  # create formatter and add it to the handlers
  formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  ch.setFormatter(formatter)
  fh.setFormatter(formatter)
  # add the handlers to logger
  logger.addHandler(ch)
  logger.addHandler(fh)
  

server_logger = logging.getLogger('ping.server')  
if __name__ == '__main__':
  server_logger.info('-' * 40)
  server_logger.info('Preparing server for launch...')

import json
# set FloatBoat's config globally so that
# blueprints and other things can access it
try:
  CONFIG = json.loads(open('config.json', 'r').read())
  server_logger.info('Loaded config.json successfully')
  
except:
  server_logger.error('Could not load config.json please verify that it is there or it is valid JSON')
  os.exit()
  
# import all of the packages we will need
import sanic # our framework of choice
from sanic import response
from sanic_session import InMemorySessionInterface
from sanic_jinja2 import SanicJinja2

# for /setup
from passlib.hash import argon2
import os
import binascii

# our db of choice
import pymongo
db_connection = pymongo.MongoClient(CONFIG['mongodb_location'])

db = db_connection.floatboat

from sanic_openapi import swagger_blueprint, openapi_blueprint, doc


# gotta' go fast(er)
app = sanic.Sanic()

app.config.API_VERSION = '0.2a'
app.config.API_TITLE = 'Ping API'
app.config.API_DESCRIPTION = 'Ping - The open-source video platform'
app.config.API_TERMS_OF_SERVICE = 'terms-of-service'
app.config.API_PRODUCES_CONTENT_TYPES = ['application/json']
app.config.API_CONTACT_EMAIL = 'cerulean.connor@gmail.com'


app.blueprint(openapi_blueprint)
app.blueprint(swagger_blueprint)
# set sanic to listen on /cdn for static
# file system
app.static('/cdn', './static')

jinja = SanicJinja2(app)

# Now we add the config to the jinja global vars
# this allows us to do {{config.site_name}} for instance
jinja.add_env('config', CONFIG)
app.config['floatboat'] = CONFIG

session = InMemorySessionInterface(cookie_name=app.name, prefix=app.name)

@app.middleware('request')
async def add_session_to_request(request):
    # before each request initialize a session
    # using the client's request
    await session.open(request)
    
    if request['session'].get('token'):
      # ok so user exists
      # lets fill in request.session.user with a user object
      user = db.users.find_one({'token': request['session']['token']})
      if user is None:
        # token is invalid
        # log them out and reset the session
        request['session']['token'] = ''
        try:
          del request['session']['user']
        except KeyError:
          # didnt exist in the first place
          pass
        
      else:
        # not needed in day to day life of a user object
        del user['_id']
        del user['password_hash']
        del user['token'] 
        
        # ok now we need to add the role permissions
        # to the user object for more fine control
        # over what someone can do
        user['permissions'] = ROLES[user['role']]
        for k, v in DEFAULT_PERMISSIONS.items():
          if k not in user['permissions']:
            # missing value in perms
            # lets add it from the DEFAULT_PERMISSIONS dict
            user['permissions'][k] = v
              
        request['session']['user'] = user
        
        
      
@app.middleware('response')
async def save_session(request, response):
    # after each request save the session,
    # pass the response to set client cookies
    await session.save(request, response)

@app.route("/")
@jinja.template('home/index.html')  # decorator method is staticmethod
async def index(request):
  """
  Basic landing page for those
  coming in from the outside
  
  """
  return {'no_padding': True}
  
  
@app.route('/reset_setup')
async def reset(request):
  CONFIG['allow_setup'] = False
  return response.redirect('/no-u')
  
@app.route('/setup', methods=['GET', 'POST'])
@jinja.template('setup/setup_1.html')
async def start_setup(request):
  """
  Only run this route once due to the impact it has
  If you re-open this in the config OR never run this,
  you are leaving yourself open to attack.
  
  This will create an owner account
  """
  if not CONFIG['allow_setup']:
    # nice try, no access
    request['flash']('Setup has been disabled by the system admin. This has been reported', 'error')
    return response.redirect('/')
  
  
  # set the setup system
  # ok so, we need to first check if the user has set up mongo correctly
  try:
    collections = db.collection_names(include_system_collections=False)
      
  except pymongo.errors.ConnectionFailure:
    # could not find the DB or auth was invalid
    return {'error': 'We couldnt find a DB at the address you have put in the config. Please check the url you have put into the config.'}
  
  # ok the DB is working fine!
  # now we promt the user to create an admin account
  
  if request.method == 'POST':
    # admin account inbound
    form = request.form
    token = binascii.hexlify(os.urandom(60)).decode() # extra long token for admin users
    new_data = {'username': form['username'][0],
                'userID': len(list(db.users.find())) + 1,
                'password_hash': argon2.hash(form['password'][0]),
                'token':token,
                'role':'owner',
                'default_avatar': form['avatar'][0]}
    
    db.users.insert_one(new_data)
    
    request['session']['token'] = token
    # ok so now that we have set this up, lets disable this in the future
    print('[CONFIG] Disabling setup page')
    CONFIG['allow_setup'] = False
    with open('config.json', 'w') as fp:
      fp.write(json.dumps(CONFIG))
    
    return response.redirect('/dashboard')
  return {'avatars': [f.split('.')[0] for f in os.listdir('users/default_avatars/')]}

if __name__ == "__main__":
  # import the blueprints
  server_logger.info('Adding blueprints to server API')
  from blueprints.auth import auth_api
  from blueprints.profile import profile_api
  from blueprints.image import image_api
  from blueprints.video import video_api
  app.blueprint(auth_api)
  app.blueprint(profile_api)
  app.blueprint(image_api)
  app.blueprint(video_api)
  server_logger.info('Listening on 0.0.0.0:{}'.format(PORT))
  app.run(host="0.0.0.0", port=PORT)
    
    