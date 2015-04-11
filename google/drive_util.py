import os

### drive_util

### has_mimetype
# Determines whether drive supports this mimetype upload
def has_mimetype(path):

    # list of not supported types
    not_supported = ['md'];

    ext = path.split("/")[-1]
    if (ext[0] is '.' or '.' not in ext):
        return 0
    elif (ext.split('.')[-1] in not_supported):
        return 0
    else:
        return 1
