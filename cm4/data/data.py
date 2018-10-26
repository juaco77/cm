"""Cloudmesh Multi Service Data Access

Usage:
  cm4 data add FILE
  cm4 data add SERVICE FILE
  cm4 data get FILE
  cm4 data get FILE DEST_FOLDER
  cm4 data del FILE
  cm4 data (ls | dir)
  cm4 data (-h | --help)
  cm4 data --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --config      Location of a cmdata.yaml file
"""

from docopt import docopt
from cm4.data.db.LocalDBProvider import LocalDBProvider
from cm4.data.storage.LocalStorageProvider import LocalStorageProvider
from cm4.data.storage.AzureStorageProvider import AzureStorageProvider
from cm4.configuration.config import Config


class Data(object):

    def __init__(self):
        self._db = None
        self._conf = {}
        self._providers = {}

    def config(self, config_path='~/.cloudmesh/cloudmesh4.yaml'):
        """
        Use `cloudmesh4.yaml` file to configure.
        """
        self._conf = Config(config_path).get("data")

        # Set DB provider. There should only be one.
        db_provider = self._conf.get('default.db')

        if db_provider == 'local':
            db_path = self._conf.get('db.local.CMDATA_DB_FOLDER')
            self._db = LocalDBProvider(db_path)

        # Check for local storage provider.
        storage_path = self._conf.get('service.local.CMDATA_STORAGE_FOLDER')
        if storage_path:
            self._providers['local'] = LocalStorageProvider(storage_path)

        # Check for Azure provider.
        az_conf = self._conf.get('service.azure')
        if az_conf:
            az_act = az_conf.get('credentials.AZURE_STORAGE_ACCOUNT')
            az_key = az_conf.get('credentials.AZURE_STORAGE_KEY')
            az_container = az_conf.get('container')
            if az_act and az_key:
                self._providers['azure'] = AzureStorageProvider(az_act, az_key, az_container)

        # Set a default storage provider.
        default_storage_provider = self._conf.get('default.service')
        self._providers['default'] = self._providers[default_storage_provider]

    def ls(self):
        """
        List tracked files.

        :return: A list of CloudFiles
        """
        files = self._db.list_files()

        self._print_row("FILE", "SERVICE", "SIZE", "URL")

        for f in files:
            self._print_row(f.name, f.service, f.size, f.url)

        return files

    def add(self, provider, file_path):
        """
        Add a new file

        :param provider: The storage provider where the file should be stored.
        :param file_path: The local path to the file.
        """
        new_cloud_file = self._providers[provider or 'default'].add(file_path)
        self._db.add(new_cloud_file)
        return new_cloud_file

    def get(self, file_name, dest_folder='.'):
        """

        Retrieve a file

        :param file_name: The name corresponding to the cloud file to be downloaded.
        :param dest_folder:
        :return:
        """
        # Get db entry for this file
        cloud_file = self._db.get(file_name)

        if not cloud_file:
            print("Requested file not found. Use `ls` to see a list of file names.")
            raise SystemExit

        # Todo: docopt default for this?
        dest_folder = dest_folder or '.'
        self._providers[cloud_file.service].get(cloud_file, dest_folder)

    def delete(self, file_name):
        """
        Remove a file

        :param file_name: The name of the file to remove.
        """
        cloud_file = self._db.get(file_name)

        if cloud_file is None:
            raise Exception(f"{file_name} not found in the database.")

        self._providers[cloud_file.service].delete(cloud_file)
        self._db.delete(cloud_file)

    def _print_row(self, file_name, service, size, url):
        """
        Print a formatted row
        """
        print(" %-35s %-10s %-10s %-50s" % (file_name, service, size, url))


if __name__ == "__main__":
    arguments = docopt(__doc__, version='Cloudmesh Drive 0.1')

    cd = Data()
    cd.config()

    if arguments['ls'] or arguments['dir']:
        cd.ls()
    elif arguments['add'] and arguments['FILE']:
        cd.add(arguments['SERVICE'], arguments['FILE'])
    elif arguments['del'] and arguments['FILE']:
        cd.delete(arguments['FILE'])
    elif arguments['get'] and arguments['FILE']:
        cd.get(arguments['FILE'], arguments['DEST_FOLDER'])