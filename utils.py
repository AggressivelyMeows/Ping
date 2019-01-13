from server import db, CONFIG, ROLES

def require_role(requires, user, type='<='):
  if isinstance(user, int):
    # is a user object
    user_role = db.users.find_one({'userID': user})
    user_role = user_role['role']
  else:
    try:
      user_role = user['role']
    except:
      user_role = user
    
  current_rank = ROLES[user_role]['rank']

  requires_rank = ROLES[requires]['rank']
  print(current_rank, requires_rank)
  if type == '<=':
    if current_rank <= requires_rank:
      return True
    
  return False

def require_auth(request):
  """
  Confirm a user is logged in
  and has the correct auth token
  """
  try:
    token = request['session']['token']
  except:
    # no token in request
    return False # NOT LOGGED IN :v
  else:
    # ok lets grab the user
    user = db.users.find_one({'token': token})
    if not user:
      # user doesnt exist
      return False
    else:
      return True # :ok_hand: user is logged in
    