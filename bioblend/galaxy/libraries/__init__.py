"""
Contains possible interactions with the Galaxy Data Libraries
"""
from bioblend.galaxy.client import Client


class LibraryClient(Client):
    def __init__(self, galaxy_instance):
        self.module = 'libraries'
        super(LibraryClient, self).__init__(galaxy_instance)

    def create_library(self, name, description=None, synopsis=None):
        """
        Create a data library with the properties defined in the arguments.
        Return a list of JSON dicts, looking like so::

            [{"id": "f740ab636b360a70",
              "name": "Library from bioblend",
              "url": "/api/libraries/f740ab636b360a70"}]

        """
        payload = {'name': name}
        if description:
            payload['description'] = description
        if synopsis:
            payload['synopsis'] = synopsis
        return Client._post(self, payload)

    def delete_library(self, library_id):
        """
        Delete a data library identified by `library_id`.

        .. warning::
            Deleting a data library is irreversible - all of the data from
            the library will be permanently deleted.
        """
        payload = {}
        return Client._delete(self, payload, id=library_id)

    def __show_item(self, library_id, item_id):
        url = self.gi._make_url(self, library_id, contents=True)
        url = '/'.join([url, item_id])
        return Client._get(self, url=url)

    def show_dataset(self, library_id, dataset_id):
        """
        Get details about a given library dataset. The required ``library_id``
        can be obtained from the datasets's library content details.
        """
        return self.__show_item(library_id, dataset_id)

    def show_folder(self, library_id, folder_id):
        """
        Get details about a given folder. The required ``folder_id``
        can be obtained from the folder's library content details.
        """
        return self.__show_item(library_id, folder_id)

    def create_folder(self, library_id, folder_name, description=None, base_folder_id=None):
        """
        Create a folder in the given library and the base folder. If
        ``base_folder_id`` is not provided, the new folder will be created
        in the root folder.
        """
        # Get root folder ID if no ID was provided
        if base_folder_id is None:
            folders = self.show_library(library_id=library_id, contents=True)
            for f in folders:
                if f['name'] == '/':
                    base_folder_id = f['id']
                    break
        # Compose the payload
        payload = {}
        payload['name'] = folder_name
        payload['folder_id'] = base_folder_id
        payload['create_type'] = 'folder'
        if description is not None:
            payload['description'] = description
        return Client._post(self, payload, id=library_id, contents=True)

    def get_folders(self, library_id, folder_id=None, name=None, deleted=False):
        """
        Get all the folders or filter specific one(s) via the provided ``name``
        or ``folder_id`` in data library with id ``library_id``. Provide only one
        argument: ``name`` or ``folder_id``, but not both.

        If ``name`` is set and multiple names match the given name, all the
        folders matching the argument will be returned.

        If ``deleted`` is set to ``True``, return folders that have been deleted.

        Return a list of JSON formatted dicts each containing basic information
        about a folder.
        """
        library_contents = Client._get(self, id=library_id, contents=True)
        folders = []
        filtered_folders = []
        for content in library_contents:
            if content['type'] == 'folder':
                folders.append(content)
                if name == content['name'] or folder_id == content['id']:
                    filtered_folders.append(content)
                if folder_id is not None and filtered_folders:
                    break
        if name is not None or folder_id is not None:
            folders = filtered_folders
        return folders

    def get_libraries(self, library_id=None, name=None, deleted=False):
        """
        Get all the libraries or filter for specific one(s) via the provided name or ID.
        Provide only one argument: ``name`` or ``library_id``.

        If ``name`` is set and multiple names match the given name, all the
        libraries matching the argument will be returned.

        Return a list of JSON formatted dicts each containing basic information
        about a library.
        """
        libraries = Client._get(self, deleted=deleted)
        if name is not None or library_id is not None:
            filtered_libs = []
            for lib in libraries:
                if name == lib['name'] or library_id == lib['id']:
                    filtered_libs.append(lib)
                # Library ID's are unique so break now that the lib was found
                if library_id is not None and filtered_libs:
                    break
            libraries = filtered_libs
        return libraries

    def show_library(self, library_id, contents=False):
        """
        Get information about a library.

        If want to get contents of the library (rather than just the library details),
        set ``contents`` to ``True``.

        Return a list of JSON formatted dicts containing library details.
        """
        return Client._get(self, id=library_id, contents=contents)

    def _do_upload(self, **keywords):
        """
        Set up the POST request and do the actual data upload to a data library.
        This method should not be called directly but instead refer to the methods
        specific for the desired type of data upload.
        """
        # If folder_id was not provided in the arguments, find the root folder ID
        if keywords.get('folder_id', None) is None:
            folders = self.show_library(library_id=keywords['library_id'], contents=True)
            for f in folders:
                if f['name'] == '/':
                    folder_id = f['id']
                    break
        else:
            folder_id = keywords['folder_id']

        files_attached = False
        # Compose the payload dict
        payload = {}
        payload['folder_id'] = folder_id
        payload['file_type'] = keywords.get('file_type', 'auto')
        payload['dbkey'] = keywords.get('dbkey', '?')
        payload['create_type'] = 'file'
        if keywords.get("roles", None):
            payload["roles"] = keywords["roles"]
        if keywords.get("link_data_only", None):
            payload["link_data_only"] = 'link_to_files'
        # upload options
        if keywords.get('file_url', None) is not None:
            payload['upload_option'] = 'upload_file'
            payload['files_0|url_paste'] = keywords['file_url']
        elif keywords.get('pasted_content', None) is not None:
            payload['upload_option'] = 'upload_file'
            payload['files_0|url_paste'] = keywords['pasted_content']
        elif keywords.get('server_dir', None) is not None:
            payload['upload_option'] = 'upload_directory'
            payload['server_dir'] = keywords['server_dir']
        elif keywords.get('file_local_path', None) is not None:
            payload['upload_option'] = 'upload_file'
            payload['files_0|file_data'] = open(keywords['file_local_path'], 'rb')
            files_attached = True
        elif keywords.get("filesystem_paths", None) is not None:
            payload["upload_option"] = "upload_paths"
            payload["filesystem_paths"] = keywords["filesystem_paths"]

        r = Client._post(self, payload, id=keywords['library_id'], contents=True,
                         files_attached=files_attached)

        if payload.get('files_0|file_data', None) is not None:
            payload['files_0|file_data'].close()

        return r

    def upload_file_from_url(self, library_id, file_url, folder_id=None, file_type='auto', dbkey='?'):
        """
        Upload a file to a library from a URL.
        If ``folder_id`` is not specified, the file will be uploaded to the root folder.
        """
        # TODO: Is there a better way of removing self from locals?
        vars = locals().copy()
        del vars['self']
        return self._do_upload(**vars)

    def upload_file_contents(self, library_id, pasted_content, folder_id=None, file_type='auto', dbkey='?'):
        """
        Upload pasted_contents to a data library as a new file.
        If ``folder_id`` is not specified, the file will be placed in the root folder.
        """
        vars = locals().copy()
        del vars['self']
        return self._do_upload(**vars)

    def upload_file_from_local_path(self, library_id, file_local_path,
                                    folder_id=None, file_type='auto', dbkey='?'):
        """
        Read local file contents from file_local_path and upload data to a library.
        If ``folder_id`` is not specified, the file will be placed in the root folder.
        """
        vars = locals().copy()
        del vars['self']
        return self._do_upload(**vars)

    def upload_file_from_server(self, library_id, server_dir, folder_id=None,
                                file_type='auto', dbkey='?', link_data_only=None,
                                roles=""):
        """
        Upload a file to a library from a path on the server where Galaxy is running.
        If ``folder_id`` is not provided, the file will be placed in the root folder.

        Note that for this method to work, the Galaxy instance you're connecting to
        must have the configuration option ``library_import_dir`` set in ``universe_wsgi.ini``.
        The value of that configuration option should be a base directory from where
        more specific directories can be specified as part of the ``server_dir`` argument.
        All and only the files (ie, no folders) specified by the ``server_dir`` argument
        will be uploaded to the data library.
        """
        vars = locals().copy()
        del vars['self']
        return self._do_upload(**vars)

    def upload_from_galaxy_filesystem(self, library_id, filesystem_paths, folder_id=None,
                                      file_type="auto", dbkey="?", link_data_only=None,
                                      roles=""):
        """Upload a file from filesystem paths already present on the Galaxy server.

        Provides API access for the 'Upload files from filesystem paths' approach.

        ``link_data_only`` -- whether to copy data into Galaxy. Setting to 'link_to_files'
          symlinks data instead of copying
        """
        vars = locals().copy()
        del vars['self']
        return self._do_upload(**vars)

    def set_library_permissions(self, library_id, access_in=None, modify_in=None, 
                                add_in=None, manage_in=None):
        """
        Sets the permissions for a library.  Note: it will override all 
        security for this library even if you leave out a permission type.
        
        access_in, modify_in, add_in, manage_in expect a list of user id's OR None
        """
        
        payload = {}
        if access_in:
            payload['LIBRARY_ACCESS_in'] = access_in
        if modify_in:
            payload['LIBRARY_MODIFY_in'] = modify_in
        if add_in:
            payload['LIBRARY_ADD_in'] = add_in
        if manage_in:
            payload['LIBRARY_MANAGE_in'] = manage_in
        
        # create the url
        url = self.url
        url = '/'.join([url, library_id, 'permissions'])
        
        return Client._post(self, payload, url=url)
        
