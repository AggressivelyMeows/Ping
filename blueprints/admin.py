from sanic import Blueprint, response
from server import jinja, db, CONFIG
from utils import require_auth


admin_api = Blueprint('admin')

@admin_api.route('/admin')
@jinja.template('admin/admin.html')
async def admin(request):
  if require_auth(request) and request['session']['user']['role'] == 'owner':
    return {}
  else:
    return response.redirect('/login?goto=admin')
  