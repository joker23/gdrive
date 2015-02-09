import os
import pprint

from apiclient import errors
from auth import get_service
from auth import get_auth_code
from apiclient.http import MediaFileUpload
from pymongo import MongoClient

### Api access for drive
# Note that this api will only be responsible for managing the files that
# are h uploaded by the application, this will not tamper with other files
# that might be in your google drive
#
# This assumes that the source of truth is from your local instance... not
# from drive.

dbclient = MongoClient('localhost', 27017)
db = dbclient.drive

""" Adds a file to the app

    Args:
        path : path to the file
        filename : name of the file
        parent_id : the id of the parent folder

    Returns:
        File metadata if successful, None otherwise
"""
def add_file(path, filename, parent_id):

    # first check for valid parameters
    if (path is None or filename is None or not os.path.isfile(path)):
        return None

    # commit the file to drive
    file_id = create_file_in_drive(get_service(), path, filename, parent_id)

    if (not file_id):
        return None

    # create object storage to mongo
    obj = {
        'drive_id' : file_id,
        'path' : path,
        'name' : filename,
        'parent_id' : parent_id
    }

    # commit to mongodb
    if (db.file.insert(obj)):
        return file_id


""" Creates a file in drive

    Args:
        service : Drive API service instance
        path : Path to the file being uploaded
        filename : The name of the file to insert
        parent_id : Parent folder's id

    Returns:
        File metadata if successful, None otherwise
"""
def create_file_in_drive(service, path, filename, parent_id):
    media_body = MediaFileUpload(path, mimetype='text/plain', resumable=True)

    body = {
        'title' : filename
    }

    if (parent_id) :
        body['parents'] = [{'id' : parent_id}]

    try :
        # TODO database redundency
        file = service.files().insert(body=body, media_body=media_body).execute()
        return file['id']

    except errors.HttpError, error :
        print 'An error occurred: %s' % error
        print 'trying to upload: %s' % path
        return None

""" Add folder to the app

    Args:
        path : path to folder
        foldername : name of the folder
        parent_id : id of the parent

    Returns:
        file metadata if successful, None otherwise
"""
def add_folder(path, foldername, parent_id):
    if (foldername is None or not os.path.isdir(path)):
        return None

    folder_id = create_folder_in_drive(get_service(), foldername, parent_id);

    if (folder_id is None):
        return None

    obj = {
        'drive_id' : folder_id,
        'name' : foldername,
        'path' : path,
        'parent_id' : parent_id
    }

    if (db.folder.insert(obj)):
        return folder_id


""" Create a folder in drive

    Args:
        service : Drive API service instance
        foldername : name of the folder
        parent_id : parent folder's id

    Returns:
        File metadata if successful, None otherwise
"""
def create_folder_in_drive(service, foldername, parent_id):
    body = {
            'title' : foldername,
            'mimeType' : 'application/vnd.google-apps.folder'
        }

    if (parent_id):
        body['parents'] = [{'id' : parent_id}]

    try:
        # TODO database redundency
        folder = service.files().insert(body=body).execute()

        return folder['id']

    except errors.HttpError, error :
        print 'An error occurred: %s' % error
        return None


""" Check if file is in database

    Args:
        path : the path to the file in local database

    Returns:
        a boolean of whether the path exists in the database
"""
def is_file_in_db(path):
    if (db.file.find_one({'path' : path})):
        return True
    else:
        return False


""" Obtains a file id from the path of the file

    Args:
        path : the path to the file in the local instance

    Returns:
        file id from the database or None if the path doesn't exist
"""
def get_file_id(path):
    found_file = db.file.find_one({'path' : path}, {'drive_id' : 1})
    if (not found_file):
        return None
    file_dict = dict(found_file)
    return file_dict['drive_id']


""" Obtains a folder id from the path of the file

    Args:
        path : the path to the file in the local instance

    Returns:
        folder id from the database or None if the path doesn't exit
"""
def get_folder_id(path):
    found_folder = db.folder.find_one({'path' : path}, {'drive_id' : 1})
    if (not found_folder):
        return None
    folder_dict = dict(found_folder)
    return folder_dict['drive_id']


""" Obtains file metadata from the database

    Args:
        path : path to file

    Returns:
        A json of representation of the file document or None if not found
"""
def get_file(path):
    found_file = db.file.find_one({'path' : path})
    if (found_file is None):
        return None

    return dict(found_file)


""" obtains file metadata for all files in the database

    Returns:
        A json list of all files or None if we won't have anything in the
        database
"""
def get_all_files():
    cursor = db.file.find({})

    return list(cursor)


""" Updates the file version in drive to match local

    Args:
        path : the path to the file in the local instance

    Returns:
        metadata of the update or None if failed
"""
def push_file_to_drive(service, path, title):
    file_id = get_file_id(path)

    print 'updating ' + path + '...'

    if (not file_id):
        print 'An error has occurred the file does not exist in the app'
        return None

    try:
        # First retrieve the file from the API.
        file = service.files().get(fileId=file_id).execute()

        # File's new metadata.
        file['title'] = title

        # File's new content.
        media_body = MediaFileUpload(path, mimetype='text/plain', resumable=True)

        # Send the request to the API.
        updated_file = service.files().update(
                fileId=file_id,
                body=file,
                media_body=media_body).execute()
        return updated_file
    except errors.HttpError, error:
        print 'An error occurred: %s' % error
        return None


""" Deletes a file from the app

    Args:
        path : path to the file

    Returns:
        True if the operation was successful, False otherwise
"""
def delete_file(path):
    file_id = get_file_id(path)

    if (not file_id):
        print 'An error has occurred the file does not exist in the app'
        return None

    if (delete_file_from_drive(get_service(), file_id)):
        if (db.file.remove({'drive_id' : file_id})):
            os.remove(path)
            return True
    return False


""" Deletes a file from google drive

    Args:
        service : google drive service object
        file_id : file id in drive

    Returns:
        returns what google returns (which is nothing if successful)
"""
def delete_file_from_drive(service, file_id):
    try:
        if (not service.files().delete(fileId=file_id).execute()):
            return True
        else:
            return False

    except errors.HttpError, error:
        print 'An error occurred: %s' % error
        return None

#def download_file(file_id):

# would going up a directory have a id? if so then that is the parent
# need to by dynamic in creating the files

### TODO pull file changes

### Retrieves all files
def retrieve_all_file():

    service = get_service()
    res = []
    page_token = None

    while True:
        try:
            param = {}
            if page_token:
                param['pageToken'] = page_token
            files = service.files().list(**param).execute()

            print files['items']
            res.extend(files['items'])
            page_token = files.get('nextPageToken')
            if not page_token:
                break

        except errors.HttpError, error:
            print 'An error occurred %s' % error
            break
    print res
