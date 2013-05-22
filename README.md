# Curse Server Modification API

Curse are providing an official Server Mods API for BukkitDev.

## Getting an API key

You can get your API key by using the page at https://dev.bukkit.org/home/servermods-apikey/.

Note: application authors should not embed their API key within their application!
Application authors should, however, ensure that they specify a unique User-Agent field.

The format:

    MyAwesomeAppName/1.0 (by lukegb)

(i.e.)

    APPNAME/VERSION (by APPLICATION_AUTHOR)

## Using the API

The API requires an API key, which should be specified using the header X-API-Key.

The API consists of the following endpoints:

### /projects

URL: https://api.curseforge.com/servermods/projects

This endpoint allows you to look up the project ID(s) which are associated to particular slugs.

This endpoint is GET only.

#### Arguments
 * search: (GET) string - search query

#### Returns
 * array of server mod objects

#### Example
	GET /servermods/projects?search=worldedit HTTP/1.1
	Host: api.curseforge.com
	X-API-Key: my-api-key-here
	User-Agent: MyAwesomeApp/v1.0 (by lukegb)

	HTTP/1.1 200 OK
	Content-Length: 13
	Content-Type: application/json; charset=utf-8
	Server: Microsoft-IIS/7.5
	X-Powered-By: ASP.NET
	Date: Thu, 14 Feb 2013 21:19:20 GMT

	[{"id":31043,"name":"WorldEdit","slug":"worldedit","stage":"release"}]

### files

URL: http://api.curseforge.com/servermods/files

This endpoint allows you to fetch the list of files for a particular set of project IDs.

This endpoint is GET only.

#### Arguments
 * projectIds: (GET) string - comma separated list of IDs

#### Returns
 * array of file objects (not that they are *not* in an object keyed on the project ID)

#### Example
	GET /files?projectIds=33921,31043
	Host: api.curseforge.com
	X-API-Key: my-api-key-here
	User-Agent: MyAwesomeApp/v1.0 (by lukegb)

	HTTP/1.1 200 OK
	Content-Length: 3034
	Content-Type: application/json; charset=utf-8
	Server: Microsoft-IIS/7.5
	X-Powered-By: ASP.NET
	Date: Mon, 11 Mar 2013 21:31:01 GMT

	[{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/553\/160\/yoda.mp3","fileName":"yoda.mp3","gameVersion":"CB 1337","name":"v0.1","projectId":33921,"releaseType":"beta"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/545\/26\/worldedit-4.7.zip","fileName":"worldedit-4.7.zip","gameVersion":"CB 1337","name":"WorldEdit 4.7","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/560\/968\/worldedit-5.0.zip","fileName":"worldedit-5.0.zip","gameVersion":"CB 1.0.1-R1","name":"WorldEdit 5.0","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/568\/218\/worldedit-5.1.zip","fileName":"worldedit-5.1.zip","gameVersion":"CB 1.0.1-R1","name":"WorldEdit 5.1","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/569\/223\/worldedit-5.1.1.zip","fileName":"worldedit-5.1.1.zip","gameVersion":"CB 1.1-R3","name":"WorldEdit 5.1.1","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/573\/609\/worldedit-5.2.zip","fileName":"worldedit-5.2.zip","gameVersion":"CB 1.1-R3","name":"WorldEdit 5.2","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/584\/135\/worldedit-5.3.jar","fileName":"worldedit-5.3.jar","gameVersion":"CB 1.2.4-R1.0","name":"WorldEdit 5.3 (jar only)","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/584\/140\/worldedit-5.3.zip","fileName":"worldedit-5.3.zip","gameVersion":"CB 1.2.5-R1.0","name":"WorldEdit 5.3","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/614\/235\/worldedit-5.4.jar","fileName":"worldedit-5.4.jar","gameVersion":"CB 1.3.1-R2.0","name":"WorldEdit 5.4 (JAR only)","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/614\/236\/worldedit-5.4.zip","fileName":"worldedit-5.4.zip","gameVersion":"CB 1.3.1-R2.0","name":"WorldEdit 5.4","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/614\/321\/worldedit-5.4.1.jar","fileName":"worldedit-5.4.1.jar","gameVersion":"CB 1.3.1-R2.0","name":"WorldEdit 5.4.1 (JAR only)","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/614\/323\/worldedit-5.4.1.zip","fileName":"worldedit-5.4.1.zip","gameVersion":"CB 1.3.1-R2.0","name":"WorldEdit 5.4.1","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/614\/411\/worldedit-5.4.2.jar","fileName":"worldedit-5.4.2.jar","gameVersion":"CB 1.3.1-R2.0","name":"WorldEdit 5.4.2 (JAR only)","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/614\/412\/worldedit-5.4.2.zip","fileName":"worldedit-5.4.2.zip","gameVersion":"CB 1.3.1-R2.0","name":"WorldEdit 5.4.2","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/639\/581\/worldedit-5.4.3.jar","fileName":"worldedit-5.4.3.jar","gameVersion":"CB 1.3.2-R2.0","name":"WorldEdit 5.4.3 (JAR only)","projectId":31043,"releaseType":"release"},{"downloadUrl":"http:\/\/addons.curse.cursecdn.com\/files\/639\/583\/worldedit-5.4.3.zip","fileName":"worldedit-5.4.3.zip","gameVersion":"CB 1.3.2-R2.0","name":"WorldEdit 5.4.3","projectId":31043,"releaseType":"release"}]
