import requests

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        raise Exception(
            "Please upgrade to Python 2.7+ or install the simplejson module."
        )

import os.path
import os


def py3():
    """ This actually returns if you're NOT running Python 2 """
    import platform
    return not platform.python_version().startswith('2')


class ServerModFile(object):
    def __init__(self, api, file_name, name, release_type, download_url,
                 game_version, project_id):
        self.api = api
        self.file_name = file_name
        self.name = name
        self.release_type = release_type
        self.download_url = download_url
        self.game_version = game_version
        self.project_id = project_id

    def __str__(self):
        return "ServerModFile: {0} ({1})".format(self.name, self.file_name)

    @classmethod
    def from_json(clz, api, dct):
        return clz(
            api=api,

            file_name=dct['fileName'],
            name=dct['name'],
            release_type=dct['releaseType'],
            download_url=dct['downloadUrl'],
            game_version=dct['gameVersion'],
            project_id=dct['projectId']
        )

    def matches_filters(self, release_type=None, extension=None):
        if release_type is not None and self.release_type != release_type:
            return False
        if extension is not None and not self.file_name.endswith(extension):
            return False
        return True


class ServerMod(object):
    def __init__(self, api, id, slug=None, name=None, stage=None):
        self.api = api
        self.id = id
        self.slug = slug
        self.name = name
        self.stage = stage

        self._files = None

    def __str__(self):
        return "ServerMod: {0}".format(self.name)

    @classmethod
    def from_json(clz, api, dct):
        return clz(
            api=api, id=dct['id'], slug=dct['slug'],
            name=dct['name'], stage=dct['stage']
        )

    def files(self):
        if self._files is not None:
            return self._files

        files = self.api.files(project_id=self.id)
        for f in files:
            f.server_mod = self  # add a back reference

        self._files = files

        return files

    def latest_file(self, **kwargs):
        files = self.files()

        # filter
        files = [f for f in files if f.matches_filters(**kwargs)]

        if len(files) == 0:
            raise NoSuchFile()

        return files[-1]


class ServerModAPIException(Exception):
    pass


class HttpErrorException(ServerModAPIException):
    def __init__(self, error_code):
        self.error_code = error_code

    def __str__(self):
        return "HttpErrorException: {0}".format(self.error_code)


class APIErrorException(ServerModAPIException):
    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        return "APIErrorException: {0} - {1}".format(
            self.obj['errorCode'], self.obj['errorMessage']
        )


class NoSuchFile(ServerModAPIException):
    pass


class ServerModAPI(object):
    base_url = "http://api.curseforge.com/servermods/"
    who_am_i = "PyServerModAPI/1.0"

    def __init__(self, api_key, who_am_i=None):
        self.api_key = api_key
        if who_am_i is not None:
            self.who_am_i = who_am_i
        self.file_cache = {}
        self.client = requests.Session()
        self.client.headers.update({
            'X-API-Key': self.api_key,
            'User-Agent': self.who_am_i
        })

    def build_url(self, url):
        return self.base_url + url

    def get(self, url, query={}):
        r = self.client.get(url, params=query)
        print r.text
        r.raise_for_status()
        data = r.json()

        if 'errorCode' in data:
            raise APIErrorException(data)

        return data

    def projects(self, search):
        query = {
            'search': search
        }
        url = self.build_url("/projects")
        return [ServerMod.from_json(self, d) for d in self.get(url, query)]

    def files(self, project_id=None, project_ids=None):
        id_query = []
        if project_id is not None:
            if int(project_id) in self.file_cache:
                return self.file_cache[int(project_id)]

            id_query = project_id
        elif project_ids is not None:
            id_query = ','.join([str(z) for z in project_ids])
        else:
            raise Exception(
                "One of project_id or project_ids must be passed into files()"
            )

        if id_query == '':
            return []

        query = {
            'projectIds': id_query
        }
        url = self.build_url("/files")
        files = [
            ServerModFile.from_json(self, d) for d in self.get(url, query)
        ]

        # cache everything
        for file in files:
            if file.project_id in self.file_cache:
                self.file_cache[file.project_id].append(file)
            else:
                self.file_cache[file.project_id] = [file]

        if project_id is not None:
            return files  # plain project ID
        else:
            file_tree = {}
            for file in files:
                if file.project_id in file_tree:
                    file_tree[file.project_id].append(file)
                else:
                    file_tree[file.project_id] = [file]


class CLIStorage(object):
    def __init__(self, folder):
        self.dir = folder
        self.path = os.path.join(folder, '.servermods.json')
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            self.data = {
                'version': 1,
                'installed': {},
                'apikey': None
            }
            self.save()
            return

        with open(self.path, 'r') as f:
            self.data = json.load(f)

    def api_key():
        doc = "The api_key property."

        def fget(self):
            return self._api_key

        def fset(self, value):
            self._api_key = value

        return {'doc': doc, 'fget': fget, 'fset': fset}
    api_key = property(**api_key())

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def get_hash(self, filename):
        import hashlib
        path = os.path.join(self.dir, filename)
        md5 = hashlib.md5()
        with open(path, 'rb') as f:
            eof = False
            while not eof:
                buf = f.read(128)  # 128 == MD5 digest block size
                if len(buf) < 128:
                    eof = True
                md5.update(buf)
        return md5.hexdigest()

    def installed(self, mod, file, filename):
        store_data = {
            'server_mod_id': mod.id,
            'server_mod_name': mod.name,
            'filename': filename,
            'file_version': file.name,
            'download_url': file.download_url,
            'hash': self.get_hash(filename)
        }
        self.data['installed'][str(mod.id)] = store_data
        return self

    def removed(self, mod, file):
        del self.data['installed'][str(mod.id)]
        return self

    def recheck(self):
        lost_files = {}
        renamed_files = {}
        known_files = set()
        dataset = self.get_data()
        for data in dataset.values():
            # does file still exist?
            if not os.path.exists(os.path.join(self.dir, data['filename'])):
                lost_files[data['hash']] = data
            else:
                known_files.add(data['filename'])

        # now check to see if they just renamed the file to confuse me
        for fn in os.listdir(self.dir):
            if fn in known_files:
                continue
            # md5 hash the file
            md5 = self.get_hash(fn)
            if md5 in lost_files.keys():
                # identified!
                renamed_file = lost_files[md5]
                smid = str(renamed_file['server_mod_id'])

                renamed_file['filename'] = fn
                renamed_files[smid] = renamed_file

        # now delete all the files from the DB that we still don't know about
        for data in lost_files.values():
            del dataset[str(data['server_mod_id'])]

        # and add all the renamed files back in
        for data in renamed_files.values():
            dataset[str(data['server_mod_id'])] = data

        self.data['installed'] = dataset

        return self

    def get_data(self):
        return self.data['installed']


class CommandLineClient(object):
    BUFSIZE = 1024

    def __init__(self, api_cls=ServerModAPI):
        try:
            import argparse
        except ImportError:
            raise Exception("Please upgrade to Python 2.7+ to use this tool.")

        self.api_cls = api_cls

        self.parser = parser = argparse.ArgumentParser()
        parser.add_argument(
            '--verbose', action='store_true',
            help='output more debugging messages'
        )
        parser.add_argument(
            '--plugins-dir',
            help='plugins directory to download files into', nargs='?'
        )
        parser.add_argument(
            '--api-key',
            help='Server Mod API key from ' +
            'https://dev.bukkit.org/home/servermods-apikey/',
            nargs='?'
        )

        subparsers = parser.add_subparsers(help='sub-command help')

        parser_search = subparsers.add_parser(
            'search', help='search for a server mod'
        )
        parser_search.add_argument(
            'query', help='search terms (e.g. the server mods\' name' +
            ' - "My Favourite Plugin")', nargs='+')
        parser_search.set_defaults(func=self.cmd_search)

        parser_install = subparsers.add_parser(
            'install', help='install a server mod'
        )
        parser_install.add_argument(
            'slug', help='server mod slugs to install', nargs='+'
        )
        parser_install.set_defaults(func=self.cmd_install)

        parser_update = subparsers.add_parser(
            'update', help='update all your server mods'
        )
        parser_update.set_defaults(func=self.cmd_update)

    def run(self):
        args = self.parser.parse_args()
        if 'func' not in args:
            self.parser.print_help()
            return
        self.api = self._fetch_api(self._get_api_key(args))
        args.func(args)

    def _get_api_key(self, args):
        if 'api_key' in args:
            return args.api_key
        plugins_dir = self.canonicalise_plugins_dir(args)
        storage = self._get_storage(plugins_dir)
        if storage.api_key is None:
            raise Exception(
                "You need to tell me what your --api-key is! " +
                "Get yours from https://dev.bukkit.org/home/servermods-apikey/"
            )
        return storage.api_key

    def _fetch_api(self, api_key):
        return self.api_cls(api_key)

    def _get_mods_for_query(self, queries):
        query_mods = {}
        for query in queries:
            query_mods[query] = self.api.projects(query)
        return query_mods

    def _get_mods_for_slugs(self, slugs):
        query_mods = self._get_mods_for_query(slugs)
        slug_mods = {}
        for slug, mods in query_mods.items():
            chosen_mod = None
            for mod in mods:
                if mod.slug == slug:
                    chosen_mod = mod
                    break
            slug_mods[slug] = chosen_mod
        return slug_mods

    def _get_storage(self, plugins_dir):
        return CLIStorage(plugins_dir)

    def canonicalise_plugins_dir(self, args):
        # check that plugins_dir exists
        plugins_dir = args.plugins_dir
        if plugins_dir is None:
            plugins_dir = 'plugins/'
        # canonicalize
        plugins_dir = os.path.abspath(plugins_dir)
        if not os.path.exists(plugins_dir):
            self.parser.error("The folder " + plugins_dir + " doesn't exist" +
                              " or is not a folder. Please tell me where " +
                              "your plugins folder is by adding:" +
                              " --plugins-dir=/home/minecraft/plugins")
        return plugins_dir

    def print_status(self, msg):
        import sys
        sys.stderr.write(msg + '                     \r')

    def print_progress(self, file, position, size,
                       file_num=None, total_files=None):
        import math
        prefix = ""
        if file_num is not None and total_files is not None:
            prefix = "[{0}/{1}] ".format(file_num, total_files)

        if position == -1 or size == -1:
            str_progress = "starting..."
        else:
            progress = int(math.floor((position * 100.0) / size))
            str_progress = "{0}%".format(progress)
        self.print_status("{2}Downloading {0}: {1}           ".format(
            file.server_mod.name, str_progress, prefix
        ))

    def await_ok(self):
        try:
            # Python 2
            inp = raw_input
        except:
            # Python 3
            inp = input
        while True:
            ok_str = inp("Is this OK? (Y/N) ").lower()
            if ok_str == 'y' or ok_str == 'yes':
                return True
            elif ok_str == 'n' or ok_str == 'no':
                return False

    def download(self, file, into, fn, file_num=None, total_files=None):
        outpath = os.path.join(into, fn)
        # download into the server mod's slug so that we overwrite previous
        # version of the same mod

        url = file.download_url

        self.print_progress(file, -1, -1, file_num, total_files)

        # ok, open the session
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        sock = resp.raw
        file_size = int(resp.headers['Content-Length'])

        current_position = 0
        outfile = open(outpath, 'wb')
        while True:
            buf = sock.read(self.BUFSIZE)
            current_position += len(buf)
            self.print_progress(
                file, current_position, file_size, file_num, total_files
            )
            outfile.write(buf)
            if len(buf) < self.BUFSIZE:
                break

        outfile.close()
        print("")

        return fn

    def clean_mods_for_slugs(self, slugs):
        mods = self._get_mods_for_slugs(slugs)

        # could any slugs not be found?
        if None in mods.values():
            unfound = [slug for slug, mod in mods.items() if mod is None]
            unfound_str = '"' + '", "'.join(unfound) + '"'
            self.parser.error(
                'Couldn\'t find the following server mods ' +
                '(try using "search" to find their slugs): ' + unfound_str
            )

        return mods

    def cmd_search(self, args):
        self.print_status("Searching server mods...")
        mods_by_query = self._get_mods_for_query(args.query)
        for query, mods in mods_by_query.items():
            if len(mods) == 0:
                print("There were no results for '{0}'".format(query))
                print("")
                continue

            print("Search results for '{0}'".format(query))
            for mod in mods:
                extra = ""
                if mod.stage != "release":
                    extra = " [stage: {0}]".format(mod.stage)
                print(" - {0} (slug: {1}){2}".format(
                    mod.name, mod.slug, extra
                ))
            print("")

    def cmd_install(self, args):
        plugins_dir = self.canonicalise_plugins_dir(args)

        self.print_status("Loading persistent storage...")
        storage = self._get_storage(plugins_dir)

        self.print_status("Fetching server mods...")
        mods = self.clean_mods_for_slugs(args.slug)

        # start building a list of files to download
        self.print_status("Building list of files...")
        lacking_jars = []
        files_to_fetch = []
        self.api.files(project_ids=[m.id for m in mods.values()])
        for slug, mod in mods.items():
            try:
                f = mod.latest_file(extension='.jar')
                files_to_fetch.append((mod, f))
            except:
                lacking_jars.append(slug)

        if len(lacking_jars) > 0:
            lacking_jars_str = '"' + '", "'.join(lacking_jars) + '"'
            self.parser.error(
                'Some of those server mods have no plain JAR ' +
                'files, so I can\'t install them: ' + lacking_jars_str
            )

        # OK, it's showtime!
        print("Going to download:             ")  # spaces to clear line
        for mod, f in files_to_fetch:
            print(" - {0}: {1} ({2})".format(mod.name, f.name, f.release_type))
        print("")
        print("These will be downloaded directly into " + plugins_dir)
        print("")

        ok = self.await_ok()
        if not ok:
            return

        print("")

        n = 0
        file_count = len(files_to_fetch)
        for mod, f in files_to_fetch:
            n += 1
            fn = self.download(
                file=f, into=plugins_dir, file_num=n, total_files=file_count,
                fn=f.server_mod.slug + '.jar'
            )
            storage.installed(mod=mod, file=f, filename=fn)

        self.print_status("Cleaning up...")
        storage.save()

    def cmd_update(self, args):
        plugins_dir = self.canonicalise_plugins_dir(args)

        self.print_status("Loading persistent storage...")
        storage = self._get_storage(plugins_dir)

        update_queue = []

        self.print_status("Checking installed plugins...")
        storage.recheck()

        update_queue = storage.get_data()
        self.print_status("Checking for updates...")
        self.api.files(
            project_ids=[m for m in update_queue.keys()]
        )  # seed cache

        if len(update_queue) == 0:
            self.parser.error("You don't have anything to update yet!")

        up_to_date = []
        files_to_fetch = []
        lacking_jars = []
        for data in update_queue.values():
            mod = ServerMod(
                self.api, data['server_mod_id'], name=data['server_mod_name']
            )
            try:
                f = mod.latest_file(extension='.jar')
                if f.download_url == data['download_url']:
                    up_to_date.append([data, f])
                else:
                    files_to_fetch.append([data, f])
            except:
                lacking_jars.append(data)

        print("Summary:                ")
        if len(lacking_jars) > 0:
            print(" No change (lacking JARs)")
            for data in lacking_jars:
                print(" - {0}".format(data['server_mod_name']))
            print("")
        if len(up_to_date) > 0:
            print(" No change (up to date)")
            for data, f in up_to_date:
                print(" - {0} ({1})".format(data['server_mod_name'], f.name))
            print("")
        if len(files_to_fetch) > 0:
            print(" Going to update")
            for data, f in files_to_fetch:
                print(" - {0} ({1} --> {2})".format(
                    data['server_mod_name'], data['file_version'], f.name
                ))
            print("")

        if len(files_to_fetch) == 0:
            return

        print("These will be downloaded directly into " + plugins_dir)
        print("")

        ok = self.await_ok()
        if not ok:
            return

        n = 0
        file_count = len(files_to_fetch)
        for data, f in files_to_fetch:
            n += 1
            fn = self.download(
                file=f, into=plugins_dir, file_num=n, total_files=file_count,
                fn=data['filename']
            )
            storage.installed(mod=mod, file=f, filename=fn)

        self.print_status("Cleaning up...")
        storage.save()


if __name__ == '__main__':
    clc = CommandLineClient()
    clc.run()
