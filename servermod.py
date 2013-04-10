try:
    import urllib2 as urllib_req
    import urllib as urllib_par
except ImportError:
    import urllib.request as urllib_req
    import urllib.parse as urllib_par

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        raise Exception("Please upgrade to Python 2.7+ or install the simplejson module.")

def py3():
    """ This actually returns if you're NOT running Python 2 """
    import platform
    return not platform.python_version().startswith('2')

class ServerModFile(object):
    def __init__(self, api, file_name, name, release_type, download_url, game_version, project_id):
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

            file_name = dct['fileName'],
            name = dct['name'],
            release_type = dct['releaseType'],
            download_url = dct['downloadUrl'],
            game_version = dct['gameVersion'],
            project_id = dct['projectId']
        )

    def matches_filters(self, release_type=None, extension=None):
        if release_type is not None and self.release_type != release_type:
            return False
        if extension is not None and not self.file_name.endswith(extension):
            return False
        return True

class ServerMod(object):
    def __init__(self, api, id, slug, name, stage):
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
        return clz(api=api, id=dct['id'], slug=dct['slug'], name=dct['name'], stage=dct['stage'])

    def files(self):
        if self._files is not None:
            return self._files

        files = self.api.files(project_id=self.id)
        for f in files:
            f.server_mod = self # add a back reference

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
        return "APIErrorException: {0} - {1}".format(self.obj['errorCode'], self.obj['errorMessage'])

class NoSuchFile(ServerModAPIException): pass

class ServerModAPI(object):
    base_url = "http://api-server-mods.curse.local"
    who_am_i = "PyServerModAPI/1.0"

    def __init__(self, api_key, who_am_i=None):
        self.api_key = api_key
        if who_am_i is not None:
            self.who_am_i = who_am_i
        self.file_cache = {}

    def build_url(self, url, query=None):
        if query is None:
            return self.base_url + url
        else:
            return self.base_url + url + "?" + urllib_par.urlencode(query)

    def get(self, url):
        # build headers
        headers = {
            'X-API-Key': self.api_key,
            'User-Agent': self.who_am_i
        }

        request = urllib_req.Request(url, headers=headers)
        f = urllib_req.urlopen(request) # open socket

        # did the request succeed?
        if f.getcode() != 200:
            raise HttpErrorException(f.getcode())

        # decode the data
        if py3():
            str_data = f.readall().decode('utf-8') # python 3 mode
            data = json.loads(str_data)
        else:
            data = json.load(f)
        f.close()

        if 'errorCode' in data:
            raise APIErrorException(data)

        return data

    def projects(self, search):
        query = {
            'search': search
        }
        url = self.build_url("/projects", query)
        return [ServerMod.from_json(self, d) for d in self.get(url)]

    def files(self, project_id=None, project_ids=None):
        id_query = []
        if project_id is not None:
            if int(project_id) in self.file_cache:
                return self.file_cache[int(project_id)]

            id_query = project_id
        elif project_ids is not None:
            id_query = ','.join([str(z) for z in project_ids])
        else:
            raise Exception("One of project_id or project_ids must be passed into files()")

        query = {
            'projectIds': id_query
        }
        url = self.build_url("/files", query)
        files = [ServerModFile.from_json(self, d) for d in self.get(url)]

        # cache everything
        for file in files:
            if file.project_id in self.file_cache:
                self.file_cache[file.project_id].append(file)
            else:
                self.file_cache[file.project_id] = [file]

        if project_id is not None:
            return files # plain project ID

class CommandLineClient(object):
    BUFSIZE = 1024

    def __init__(self, api):
        try:
            import argparse
        except ImportError:
            raise Exception("Please upgrade to Python 2.7+ to use this tool.")

        self.api = api

        self.parser = parser = argparse.ArgumentParser()
        parser.add_argument('--verbose', action='store_true', help='output more debugging messages')

        subparsers = parser.add_subparsers(help='sub-command help')

        parser_search = subparsers.add_parser('search', help='search for a server mod')
        parser_search.add_argument('query', help='search terms (e.g. the server mods\' name - "My Favourite Plugin")', nargs='+')
        parser_search.set_defaults(func=self.cmd_search)

        parser_install = subparsers.add_parser('install', help='install a server mod')
        parser_install.add_argument('slug', help='server mod slugs to install', nargs='+')
        parser_install.add_argument('--plugins-dir', help='plugins directory to download files into', nargs='?')
        parser_install.set_defaults(func=self.cmd_install)

    def run(self):
        args = self.parser.parse_args()
        if 'func' not in args:
            self.parser.print_help()
            return
        args.func(args)

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

    def print_status(self, msg):
        import sys
        sys.stderr.write(msg + '\r')

    def print_progress(self, file, position, size, file_num=None, total_files=None):
        import math
        prefix = ""
        if file_num is not None and total_files is not None:
            prefix = "[{0}/{1}] ".format(file_num, total_files)

        if position == -1 or size == -1:
            str_progress = "starting..."
        else:
            progress = int(math.floor((position * 100.0) / size))
            str_progress = "{0}%".format(progress)
        self.print_status("{2}Downloading {0}: {1}           ".format(file.server_mod.name, str_progress, prefix))

    def await_ok(self):
        try:
            # Python 2 (it also has input, but that takes a Python expression...)
            inp = raw_input
        except:
            # Python 3 (raw_input --> input)
            inp = input
        while True:
            ok_str = inp("Is this OK? (Y/N) ").lower()
            if ok_str == 'y' or ok_str == 'yes':
                return True
            elif ok_str == 'n' or ok_str == 'no':
                return False

    def download(self, file, into, file_num=None, total_files=None):
        import os.path
        outpath = os.path.join(into, file.server_mod.slug + '.jar')
        # download into the server mod's slug so that we overwrite previous version of the same mod

        url = file.download_url

        self.print_progress(file, -1, -1, file_num, total_files)

        # ok, open the session
        sock = urllib_req.urlopen(url)
        headers = sock.info()
        file_size = int(headers['Content-Length'])

        current_position = 0
        outfile = open(outpath, 'wb')
        while True:
            buf = sock.read(self.BUFSIZE)
            current_position += len(buf)
            self.print_progress(file, current_position, file_size, file_num, total_files)
            outfile.write(buf)
            if len(buf) < self.BUFSIZE:
                break

        outfile.close()
        sock.close()
        print("")

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
                print(" - {0} (slug: {1}){2}".format(mod.name, mod.slug, extra))
            print("")

    def cmd_install(self, args):
        import os.path
        # check that plugins_dir exists
        plugins_dir = args.plugins_dir
        if plugins_dir is None:
            plugins_dir = 'plugins/'
        # canonicalize
        plugins_dir = os.path.abspath(plugins_dir)
        if not os.path.exists(plugins_dir):
            self.parser.error("The folder " + plugins_dir + " doesn't exist or is not a folder. Please tell me where your plugins folder is by adding: --plugins-dir=/home/minecraft/plugins")

        self.print_status("Fetching server mods...")
        mods = self._get_mods_for_slugs(args.slug)

        # could any slugs not be found?
        if None in mods.values():
            unfound = [slug for slug,mod in mods.items() if mod is None]
            unfound_str = '"' + '", "'.join(unfound) + '"'
            self.parser.error('Couldn\'t find the following server mods (try using "search" to find their slugs): ' + unfound_str)

        # start building a list of files to download
        self.print_status("Building list of files...")
        lacking_jars = []
        files_to_fetch = []
        self.api.files(project_ids=[m.id for m in mods.values()])
        for slug, mod in mods.items():
            try:
                f = mod.latest_file(extension='.jar')
                files_to_fetch.append([mod, f])
            except:
                lacking_jars.append(slug)

        if len(lacking_jars) > 0:
            lacking_jars_str = '"' + '", "'.join(lacking_jars) + '"'
            self.parser.error('Some of those server mods have no plain JAR files, so I can\'t install them: ' + lacking_jars_str)

        # OK, it's showtime!
        print("Going to download:             ") # spaces are for padding for clearing status messages
        for mod, f in files_to_fetch:
            print(" - {0}: {1} ({2})".format(mod.name, f.name, f.release_type))
        print("")
        print("These will be downloaded directly into plugins/")
        print("")

        ok = self.await_ok()
        if not ok:
            return

        print("")

        n = 0
        file_count = len(files_to_fetch)
        for mod, f in files_to_fetch:
            n += 1
            self.download(file=f, into=plugins_dir, file_num=n, total_files=file_count)

if __name__ == '__main__':
    clc = CommandLineClient(ServerModAPI("z76dgHas!jsda"))
    clc.run()