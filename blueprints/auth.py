from sanic import Blueprint, response
from server import jinja, db, CONFIG

# security related stuffs
from passlib.hash import argon2
import os
import binascii

from datetime import datetime

auth_api = Blueprint('auth')

@auth_api.route('/login', methods=['GET', 'POST'])
@jinja.template('auth/login.html')
async def auth_user(request):
  if request.method == 'POST':
    form = request.form
    user = db.users.find_one({'username': form['username'][0]})
    if not user:
      return {'error':'username/password is incorrect'}
    
    if argon2.verify(form['password'][0], user['password_hash']):
      request['session']['token'] = user['token']
      
      if 'goto' in request.raw_args:
        if '/' not in request.raw_args['goto']:
          return response.redirect('/' + request.raw_args['goto'])
      
      return response.redirect('/')
    
    else:
      return {'error':'username/password is incorrect'}
    
  return {}
 
@auth_api.route('/signup', methods=['GET', 'POST'])
@jinja.template('auth/signup.html')
async def auth_user(request):
  if request.method == 'POST':
    if not CONFIG['allow_signups']:
      return {'error': 'Sorry, we are not accepting any new members right now!'}
    form = request.form
    # returns the form as a dict of lists
    # kinda fucky when you try to actually access any data on the form
    # this is a problem and ill have to try and find a way to unpack these to make it better to use
    # in the future.
    check_user = db.users.find_one({'username': form['username'][0]})
    if check_user is not None:
      return {'error': 'Username is already taken'}
    
    token = binascii.hexlify(os.urandom(20)).decode()
    
    new_user = {
      'username': form['username'][0],
      'userID': len(list(db.users.find())) + 1,
      'password_hash': argon2.hash(form['password'][0]),
      'token':token,
      'created_at': datetime.utcnow().timestamp(),
      'default_avatar':'',
      'role': CONFIG.get('signup_default_role', 'viewer')
    }
    db.users.insert_one(new_user)
    
    request['session']['token'] = token
    return response.redirect('/')
  return {}
  
@auth_api.route('/api/v1/auth/check_username')
async def utils_check_username(request):
  if 'username' in request.args:
    user = db.users.find_one({'username': request.args['username']})
    return response.json({'result': True if user else False})