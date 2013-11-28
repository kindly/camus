import requests
import json
from camus.extensions import login_manager
from flask.ext.login import login_user, current_user, logout_user

class User(object):
    def __init__(self, email):
        self.email = email
    def is_authenticated(self):
        return True
    def is_active(self):
        return True
    def is_anonymous(self):
        return False
    def get_id(self):
        return self.email

@login_manager.user_loader
def load_user(email):
    return User(email)

def login(context, form_dict):
    data = {'assertion': form_dict['assertion'], 'audience': '0.0.0.0'}
    resp = requests.post('https://verifier.login.persona.org/verify', data=data, verify=True)
    
    # Did the verifier respond?
    if resp.ok:
        # Parse the response
        verification_data = json.loads(resp.content)

        # Check if the assertion was valid
        if verification_data['status'] == 'okay':
            # Log the user in by setting a secure session cookie
            email = verification_data['email']
            login_user(User(email))
            return email

def logout(context):
    logout_user()

def get_user_dict(context):
    email = None
    if current_user.is_authenticated():
        email = current_user.email
    
    return {"user_email": email}
