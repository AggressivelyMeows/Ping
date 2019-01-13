from sanic import Blueprint, response
from server import jinja, db

import os

profile_api = Blueprint('profile')

@profile_api.route('/dashboard')
@jinja.template('profile/dashboard.html')
async def show_dashboard(request):
  if not request['session'].get('token'):
    # not logged in
    return response.redirect('/login?goto=dashboard')
  
  videos = list(db.videos.find({'author': request['session']['user']['userID']}))
  return {'videos': videos}

@profile_api.route('/dashboard/edit', methods=['GET','POST'])
@jinja.template('profile/dashboard_edit.html')
async def show_dashboard(request):
  if not request['session'].get('token'):
    # not logged in
    return response.redirect('/login?goto=dashboard')
  
  if request.method == 'POST':
    form = request.form
    changes = {}
    if form['username'][0] != request['session']['user']['username']:
      # changed username
      changes['username'] = form['username'][0]
     
    if form['avatar'][0] != request['session']['user']['default_avatar']:
      changes['default_avatar'] = form['avatar'][0]
      
    if changes:
      db.users.update_one({'token': request['session']['token']}, {'$set': changes})
    return response.redirect('/dashboard')
  
  return {'avatars': [f.split('.')[0] for f in os.listdir('users/default_avatars/')]}

@profile_api.route('/api/v1/discord')
@jinja.template('profile/embed.html')
async def show_user(request):
  user = db.users.find_one({'userID':int(request.args.get('userID', ['0'])[0])})
  if not user:
    return {}
  return {'user': user}
