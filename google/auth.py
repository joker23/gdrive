import logging
import httplib2
import pprint
import webbrowser
import os
import json

from bson import json_util
from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import Credentials
from pymongo import MongoClient

# Mongo client
dbclient = MongoClient('localhost', 27017)

# Mongo database
db = dbclient.drive_key

# Client credential json
client = db.client.find_one({'app_id' : 'gdrive'})
client_dict = dict(client)

# Copy your credentials from the console
CLIENT_ID = client_dict['client_id']
CLIENT_SECRET = client_dict['client_secret']

# Check https://developers.google.com/drive/scopes for all available scopes
OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'

# Redirect URI for installed apps
REDIRECT_URI = client_dict['redirect_uris']


""" Stores the user credentials into the application database

    Args:
        credentials : Google credentials object for auth
    Returns:
        Id of the newly created object or None if operation fails
"""
def store_credentials(credentials):
     # clear the existing credential
     db.credentials.remove({'app_id' : 'gdrive'})
     credential_json = json.JSONDecoder().decode(credentials.to_json())

     credential_json['app_id'] = 'gdrive'
     # insert the new credentials into the database
     return db.credentials.insert(credential_json)


""" Obtains a stored credential

    Returns:
        Credential in json format or None if it does not exist
"""
def get_stored_credentials():
    cred = db.credentials.find_one({'app_id' : 'gdrive'})
    cred_json = json.dumps(cred, default=json_util.default)

    ret = Credentials.new_from_json(cred_json)
    return ret


""" Gets flow parameter

    Returns:
        flow parameter
"""
def get_flow():
    flow = OAuth2WebServerFlow(CLIENT_ID, CLIENT_SECRET, OAUTH_SCOPE,
            redirect_uri=REDIRECT_URI)
    return flow

""" Obtains a fresh authentications code

    Returns:
        Authentication code
"""
def get_auth_code():
    flow = get_flow()

    authorize_url = flow.step1_get_authorize_url()
    pprint(authorize_url)
    code = raw_input('Enter verification code: ').strip()
    credentials = exchange_code(code)
    store_credentials(credentials)
    return code


""" Obtain OAuth 2.0 credentials from authorization code

    Args:
        authorization_code : The authorization code for code exchange
    Retruns:
        The credentials for the users or None if an error occurs
"""
def exchange_code(authorization_code):
    flow = get_flow()

    try:
        credentials = flow.step2_exchange(authorization_code)
        return credentials
    except error:
        logging.error('An error occurred: %s', error)
        return None

""" Obtain an authorized http instance

    Returns:
        The drive service required for drive operations
"""
def get_service():
    credentials = get_stored_credentials()

    http = httplib2.Http()
    credentials.refresh(http)
    http = credentials.authorize(http)

    drive_service = build('drive', 'v2', http=http)
    store_credentials(credentials)

    return drive_service
