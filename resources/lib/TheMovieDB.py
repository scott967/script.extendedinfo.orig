# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from YouTube import *
from Utils import *
from local_db import compare_with_library, get_imdb_id_from_db
import threading
import re
from urllib2 import Request, urlopen

TMDB_KEY = '34142515d9d23817496eeb4ff1d223d0'
POSTER_SIZES = ["w92", "w154", "w185", "w342", "w500", "w780", "original"]
LOGO_SIZES = ["w45", "w92", "w154", "w185", "w300", "w500", "original"]
BACKDROP_SIZES = ["w300", "w780", "w1280", "original"]
PROFILE_SIZES = ["w45", "w185", "h632", "original"]
STILL_SIZES = ["w92", "w185", "w300", "original"]
HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'User-agent': 'XBMC/14.0 ( phil65@kodi.tv )'
}
base_url = ""
poster_size = ""
fanart_size = ""
include_adult = str(ADDON.getSetting("include_adults")).lower()
if ADDON.getSetting("use_https"):
    url_base = "https://api.themoviedb.org/3/"
else:
    url_base = "http://api.themoviedb.org/3/"


def checkLogin():
    if ADDON.getSetting("tmdb_username"):
        session_id = get_session_id()
        if session_id:
            return "True"
    return ""


def get_rating_from_user():
    ratings = []
    for i in range(1, 21):
        ratings.append(str(float(i * 0.5)))
    rating = xbmcgui.Dialog().select(ADDON.getLocalizedString(32129), ratings)
    if rating > -1:
        return (float(rating) * 0.5) + 0.5
    else:
        return None


def send_rating_for_media_item(media_type, media_id, rating):
    # media_type: movie, tv or episode
    # media_id: tmdb_id / episode ident array
    # rating: ratung value (0.5-10.0, 0.5 steps)
    if checkLogin():
        session_id_string = "session_id=" + get_session_id()
    else:
        session_id_string = "guest_session_id=" + get_guest_session_id()
    values = '{"value": %.1f}' % rating
    if media_type == "episode":
        url = url_base + "tv/%s/season/%s/episode/%s/rating?api_key=%s&%s" % (str(media_id[0]), str(media_id[1]), str(media_id[2]), TMDB_KEY, session_id_string)
    else:
        url = url_base + "%s/%s/rating?api_key=%s&%s" % (media_type, str(media_id), TMDB_KEY, session_id_string)
    log(url)
    request = Request(url, data=values, headers=HEADERS)
    response = urlopen(request).read()
    results = simplejson.loads(response)
    # prettyprint(results)
    notify(ADDON_NAME, results["status_message"])


def change_fav_status(media_id=None, media_type="movie", status="true"):
    session_id = get_session_id()
    account_id = get_account_info()
    values = '{"media_type": "%s", "media_id": %s, "favorite": %s}' % (media_type, str(media_id), status)
    url = url_base + "account/%s/favorite?session_id=%s&api_key=%s" % (str(account_id), str(session_id), TMDB_KEY)
    log(url)
    request = Request(url, data=values, headers=HEADERS)
    response = urlopen(request).read()
    results = simplejson.loads(response)
    # prettyprint(results)
    notify(ADDON_NAME, results["status_message"])


def CreateList(listname):
    session_id = get_session_id()
    url = url_base + "list?api_key=%s&session_id=%s" % (TMDB_KEY, session_id)
    values = {'name': '%s' % listname, 'description': 'List created by ExtendedInfo Script for Kodi.'}
    request = Request(url, data=simplejson.dumps(values), headers=HEADERS)
    response = urlopen(request).read()
    results = simplejson.loads(response)
    # prettyprint(results)
    notify(ADDON_NAME, results["status_message"])
    return results["list_id"]


def remove_list(list_id):
    session_id = get_session_id()
    url = url_base + "list/%s?api_key=%s&session_id=%s" % (list_id, TMDB_KEY, session_id)
    log("Remove List: " + url)
    # prettyprint(results)
    values = {'media_id': list_id}
    request = Request(url, data=simplejson.dumps(values), headers=HEADERS)
    request.get_method = lambda: 'DELETE'
    response = urlopen(request).read()
    results = simplejson.loads(response)
    notify(ADDON_NAME, results["status_message"])
    return results["list_id"]


def change_list_status(list_id, movie_id, status):
    if status:
        method = "add_item"
    else:
        method = "remove_item"
    session_id = get_session_id()
    url = url_base + "list/%s/%s?api_key=%s&session_id=%s" % (list_id, method, TMDB_KEY, session_id)
    log(url)
    values = {'media_id': movie_id}
    request = Request(url, data=simplejson.dumps(values), headers=HEADERS)
    try:
        response = urlopen(request).read()
    except urllib2.HTTPError as err:
        if err.code == 401:
            notify("Error", "Not authorized to modify list")
    results = simplejson.loads(response)
    notify(ADDON_NAME, results["status_message"])


def GetAccountLists(cache_time=0):
    session_id = get_session_id()
    account_id = get_account_info()
    if session_id and account_id:
        response = get_tmdb_data("account/%s/lists?session_id=%s&" % (str(account_id), session_id), cache_time)
        return response["results"]
    else:
        return False


def get_account_info():
    session_id = get_session_id()
    response = get_tmdb_data("account?session_id=%s&" % session_id, 999999)
    # prettyprint(response)
    if "id" in response:
        return response["id"]
    else:
        return None


def get_certification_list(media_type):
    response = get_tmdb_data("certification/%s/list?" % media_type, 999999)
    if "certifications" in response:
        return response["certifications"]
    else:
        return None


def get_guest_session_id():
    response = get_tmdb_data("authentication/guest_session/new?", 999999)
    # prettyprint(response)
    if "guest_session_id" in response:
        return response["guest_session_id"]
    else:
        return None


def get_session_id():
    request_token = auth_request_token()
    response = get_tmdb_data("authentication/session/new?request_token=%s&" % request_token, 99999)
    # prettyprint(response)
    if response and "success" in response:
        pass_dict_to_skin({"tmdb_logged_in": "true"})
        return response["session_id"]
    else:
        pass_dict_to_skin({"tmdb_logged_in": ""})
        notify("login failed")
        return None


def get_request_token():
    response = get_tmdb_data("authentication/token/new?", 999999)
    # prettyprint(response)
    return response["request_token"]


def auth_request_token():
    request_token = get_request_token()
    username = ADDON.getSetting("tmdb_username")
    password = ADDON.getSetting("tmdb_password")
    response = get_tmdb_data("authentication/token/validate_with_login?request_token=%s&username=%s&password=%s&" % (request_token, username, password), 999999)
    # prettyprint(response)
    if "success" in response and response["success"]:
        return response["request_token"]
    else:
        return None


def handle_tmdb_multi_search(results=[]):
    listitems = []
    for item in results:
        if item["media_type"] == "movie":
            listitem = handle_tmdb_movies([item])[0]
        elif item["media_type"] == "tv":
            listitem = handle_tmdb_tvshows([item])[0]
        else:
            listitem = handle_tmdb_people([item])[0]
        listitems.append(listitem)
    return listitems


def handle_tmdb_movies(results=[], local_first=True, sortkey="Year"):
    movies = []
    ids = []
    log("starting handle_tmdb_movies")
    for movie in results:
        tmdb_id = str(fetch(movie, 'id'))
        if ("backdrop_path" in movie) and (movie["backdrop_path"]):
            backdrop_path = base_url + fanart_size + movie['backdrop_path']
        else:
            backdrop_path = ""
        if ("poster_path" in movie) and (movie["poster_path"]):
            # poster_path = base_url + poster_size + movie['poster_path']
            small_poster_path = base_url + "w342" + movie["poster_path"]
        else:
            # poster_path = ""
            small_poster_path = ""
        release_date = fetch(movie, 'release_date')
        if release_date:
            year = release_date[:4]
            time_comparer = release_date.replace("-", "")
        else:
            year = ""
            time_comparer = ""
        trailer = "plugin://script.extendedinfo/?info=playtrailer&&id=" + tmdb_id
        if ADDON.getSetting("infodialog_onclick") != "false":
            # path = 'plugin://script.extendedinfo/?info=extendedinfo&&id=%s' % tmdb_id
            path = 'plugin://script.extendedinfo/?info=action&&id=RunScript(script.extendedinfo,info=extendedinfo,id=%s)' % tmdb_id
        else:
            path = trailer
        newmovie = {'Art(fanart)': backdrop_path,
                    'Art(poster)': small_poster_path,  # needs to be adjusted to poster_path (-->skin)
                    'Thumb': small_poster_path,
                    'Poster': small_poster_path,
                    'fanart': backdrop_path,
                    'Title': fetch(movie, 'title'),
                    'Label': fetch(movie, 'title'),
                    'OriginalTitle': fetch(movie, 'original_title'),
                    'ID': tmdb_id,
                    'Path': path,
                    'media_type': "movie",
                    'country': fetch(movie, 'original_language'),
                    'plot': fetch(movie, 'overview'),
                    'Trailer': trailer,
                    'Rating': fetch(movie, 'vote_average'),
                    'credit_id': fetch(movie, 'credit_id'),
                    'character': fetch(movie, 'character'),
                    'job': fetch(movie, 'job'),
                    'department': fetch(movie, 'department'),
                    'Votes': fetch(movie, 'vote_count'),
                    'User_Rating': fetch(movie, 'rating'),
                    'Year': year,
                    'time_comparer': time_comparer,
                    'Premiered': release_date}
        if tmdb_id not in ids:
            ids.append(tmdb_id)
            movies.append(newmovie)
    movies = compare_with_library(movies, local_first, sortkey)
    return movies


def handle_tmdb_tvshows(results, local_first=True, sortkey="year"):
    tvshows = []
    ids = []
    log("starting handle_tmdb_tvshows")
    for tv in results:
        tmdb_id = fetch(tv, 'id')
        poster_path = ""
        duration = ""
        year = ""
        backdrop_path = ""
        if ("backdrop_path" in tv) and (tv["backdrop_path"]):
            backdrop_path = base_url + fanart_size + tv['backdrop_path']
        if ("poster_path" in tv) and (tv["poster_path"]):
            poster_path = base_url + poster_size + tv['poster_path']
        if "episode_run_time" in tv:
            if len(tv["episode_run_time"]) > 1:
                duration = "%i - %i" % (min(tv["episode_run_time"]), max(tv["episode_run_time"]))
            elif len(tv["episode_run_time"]) == 1:
                duration = "%i" % (tv["episode_run_time"][0])
            else:
                duration = ""
        release_date = fetch(tv, 'first_air_date')
        if release_date:
            year = release_date[:4]
        newtv = {'Art(fanart)': backdrop_path,
                 'Art(poster)': poster_path,
                 'Thumb': poster_path,
                 'Poster': poster_path,
                 'fanart': backdrop_path,
                 'Title': fetch(tv, 'name'),
                 'TVShowTitle': fetch(tv, 'name'),
                 'OriginalTitle': fetch(tv, 'original_name'),
                 'duration': duration,
                 'ID': tmdb_id,
                 'credit_id': fetch(tv, 'credit_id'),
                 'Plot': fetch(tv, "overview"),
                 'year': year,
                 'media_type': "tv",
                 'Path': 'plugin://script.extendedinfo/?info=action&&id=RunScript(script.extendedinfo,info=extendedtvinfo,id=%s)' % tmdb_id,
                 # 'Path': 'plugin://script.extendedinfo/?info=extendedtvinfo&&id=%s' % tmdb_id,
                 'Rating': fetch(tv, 'vote_average'),
                 'User_Rating': str(fetch(tv, 'rating')),
                 'Votes': fetch(tv, 'vote_count'),
                 'number_of_episodes': fetch(tv, 'number_of_episodes'),
                 'number_of_seasons': fetch(tv, 'number_of_seasons'),
                 'Release_Date': release_date,
                 'ReleaseDate': release_date,
                 'Premiered': release_date}
        if tmdb_id not in ids:
            ids.append(tmdb_id)
            tvshows.append(newtv)
    # tvshows = compare_with_library(tvshows, local_first, sortkey)
    return tvshows


def handle_tmdb_episodes(results):
    listitems = []
    for item in results:
        still_path = ""
        still_path_small = ""
        if "still_path" in item and item["still_path"]:
            still_path = base_url + "original" + item['still_path']
            still_path_small = base_url + "w300" + item['still_path']
        listitem = {'Art(poster)': still_path,
                    'Poster': still_path,
                    'Thumb': still_path_small,
                    'Title': clean_text(fetch(item, 'name')),
                    'release_date': fetch(item, 'air_date'),
                    'episode': fetch(item, 'episode_number'),
                    'production_code': fetch(item, 'production_code'),
                    'season': fetch(item, 'season_number'),
                    'Rating': fetch(item, 'vote_average'),
                    'Votes': fetch(item, 'vote_count'),
                    'ID': fetch(item, 'id'),
                    'Description': clean_text(fetch(item, 'overview'))}
        listitems.append(listitem)
    return listitems


def handle_tmdb_misc(results):
    listitems = []
    for item in results:
        poster_path = ""
        small_poster_path = ""
        if ("poster_path" in item) and (item["poster_path"]):
            poster_path = base_url + poster_size + item['poster_path']
            small_poster_path = base_url + "w342" + item["poster_path"]
        release_date = fetch(item, 'release_date')
        if release_date:
            year = release_date[:4]
        else:
            year = ""
        listitem = {'Art(poster)': poster_path,
                    'Poster': poster_path,
                    'Thumb': small_poster_path,
                    'Title': clean_text(fetch(item, 'name')),
                    'certification': fetch(item, 'certification') + fetch(item, 'rating'),
                    'item_count': fetch(item, 'item_count'),
                    'favorite_count': fetch(item, 'favorite_count'),
                    'release_date': release_date,
                    'path': "plugin://script.extendedinfo?info=listmovies&---id=%s" % fetch(item, 'id'),
                    'year': year,
                    'iso_3166_1': fetch(item, 'iso_3166_1'),
                    'author': fetch(item, 'author'),
                    'content': clean_text(fetch(item, 'content')),
                    'ID': fetch(item, 'id'),
                    'url': fetch(item, 'url'),
                    'Description': clean_text(fetch(item, 'description'))}
        listitems.append(listitem)
    return listitems


def handle_tmdb_seasons(results):
    listitems = []
    for season in results:
        year = ""
        poster_path = ""
        season_number = str(fetch(season, 'season_number'))
        small_poster_path = ""
        air_date = fetch(season, 'air_date')
        if air_date:
            year = air_date[:4]
        if ("poster_path" in season) and season["poster_path"]:
            poster_path = base_url + poster_size + season['poster_path']
            small_poster_path = base_url + "w342" + season["poster_path"]
        if season_number == "0":
            Title = "Specials"
        else:
            Title = "Season %s" % season_number
        listitem = {'Art(poster)': poster_path,
                    'Poster': poster_path,
                    'Thumb': small_poster_path,
                    'Title': Title,
                    'Season': season_number,
                    'air_date': air_date,
                    'Year': year,
                    'ID': fetch(season, 'id')}
        listitems.append(listitem)
    return listitems


def handle_tmdb_videos(results):
    listitems = []
    for item in results:
        image = "http://i.ytimg.com/vi/" + fetch(item, 'key') + "/0.jpg"
        listitem = {'Thumb': image,
                    'Title': fetch(item, 'name'),
                    'iso_639_1': fetch(item, 'iso_639_1'),
                    'type': fetch(item, 'type'),
                    'key': fetch(item, 'key'),
                    'youtube_id': fetch(item, 'key'),
                    'site': fetch(item, 'site'),
                    'ID': fetch(item, 'id'),
                    'size': fetch(item, 'size')}
        listitems.append(listitem)
    return listitems


def handle_tmdb_people(results):
    people = []
    for person in results:
        image = ""
        image_small = ""
        builtin = 'RunScript(script.extendedinfo,info=extendedactorinfo,id=%s)' % str(person['id'])
        if "profile_path" in person and person["profile_path"]:
            image = base_url + poster_size + person["profile_path"]
            image_small = base_url + "w342" + person["profile_path"]
        alsoknownas = " / ".join(fetch(person, 'also_known_as'))
        newperson = {'adult': str(fetch(person, 'adult')),
                     'name': person['name'],
                     'title': person['name'],
                     'also_known_as': alsoknownas,
                     'alsoknownas': alsoknownas,
                     'biography': clean_text(fetch(person, 'biography')),
                     'birthday': fetch(person, 'birthday'),
                     'age': calculate_age(fetch(person, 'birthday'), fetch(person, 'deathday')),
                     'character': fetch(person, 'character'),
                     'department': fetch(person, 'department'),
                     'job': fetch(person, 'job'),
                     'media_type': "person",
                     'id': str(person['id']),
                     'cast_id': str(fetch(person, 'cast_id')),
                     'credit_id': str(fetch(person, 'credit_id')),
                     'path': "plugin://script.extendedinfo/?info=action&&id=" + builtin,
                     'deathday': fetch(person, 'deathday'),
                     'place_of_birth': fetch(person, 'place_of_birth'),
                     'placeofbirth': fetch(person, 'place_of_birth'),
                     'homepage': fetch(person, 'homepage'),
                     'thumb': image_small,
                     'icon': image_small,
                     'poster': image}
        people.append(newperson)
    return people


def HandleTMDBPeopleImagesResult(results):
    images = []
    for item in results:
        image = {'aspectratio': item['aspect_ratio'],
                 'thumb': base_url + "w342" + item['file_path'],
                 'vote_average': fetch(item, "vote_average"),
                 'iso_639_1': fetch(item, "iso_639_1"),
                 'poster': base_url + poster_size + item['file_path'],
                 'original': base_url + "original" + item['file_path']}
        images.append(image)
    return images


def HandleTMDBPeopleTaggedImagesResult(results):
    images = []
    for item in results:
        image = {'aspectratio': item['aspect_ratio'],
                 'thumb': base_url + "w342" + item['file_path'],
                 'vote_average': fetch(item, "vote_average"),
                 'iso_639_1': fetch(item, "iso_639_1"),
                 'Title': fetch(item["media"], "title"),
                 'mediaposter': base_url + poster_size + fetch(item["media"], "poster_path"),
                 'poster': base_url + poster_size + item['file_path'],
                 'original': base_url + "original" + item['file_path']}
        images.append(image)
    return images


def handle_tmdb_companies(results):
    companies = []
    log("starting HandleLastFMCompanyResult")
    for company in results:
        newcompany = {'parent_company': company['parent_company'],
                      'name': company['name'],
                      'description': company['description'],
                      'headquarters': company['headquarters'],
                      'homepage': company['homepage'],
                      'id': company['id'],
                      'logo_path': company['logo_path']}
        companies.append(newcompany)
    return companies


def search_company(company_name):
    import re
    regex = re.compile('\(.+?\)')
    company_name = regex.sub('', company_name)
    response = get_tmdb_data("search/company?query=%s&" % url_quote(company_name), 10)
    try:
        return response["results"]
    except:
        log("could not find company ID")
        return ""


def multi_search(String):
    response = get_tmdb_data("search/multi?query=%s&" % url_quote(String), 1)
    if response and "results" in response:
        return response["results"]
    else:
        log("Error when searching")
        return ""


def get_person_id(person_label, skip_dialog=False):
    persons = person_label.split(" / ")
    response = get_tmdb_data("search/person?query=%s&include_adult=%s&" % (url_quote(persons[0]), include_adult), 30)
    if response and "results" in response:
        if len(response["results"]) > 1 and not skip_dialog:
            listitems = create_listitems(handle_tmdb_people(response["results"]))
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            w = SelectDialog('DialogSelect.xml', ADDON_PATH, listing=listitems)
            w.doModal()
            if w.index >= 0:
                return response["results"][w.index]
        elif response["results"]:
            return response["results"][0]
    else:
        log("could not find Person ID")
    return False


def get_keyword_id(keyword):
    response = get_tmdb_data("search/keyword?query=%s&include_adult=%s&" % (url_quote(keyword), include_adult), 30)
    if response and "results" in response and response["results"]:
        if len(response["results"]) > 1:
            names = [item["name"] for item in response["results"]]
            selection = xbmcgui.Dialog().select(ADDON.getLocalizedString(32114), names)
            if selection > -1:
                return response["results"][selection]
        elif response["results"]:
            return response["results"][0]
    else:
        log("could not find Keyword ID")
        return False


def get_set_id(setname):
    setname = setname.replace("[", "").replace("]", "").replace("Kollektion", "Collection")
    response = get_tmdb_data("search/collection?query=%s&language=%s&" % (url_quote(setname.encode("utf-8")), ADDON.getSetting("LanguageID")), 14)
    if "results" in response and response["results"]:
        return response["results"][0]["id"]
    else:
        return ""


def get_tmdb_data(url="", cache_days=14, folder=False):
    # session_id = get_session_id()
    # url = url_base + "%sapi_key=%s&session_id=%s" % (url, TMDB_KEY, session_id)
    url = url_base + "%sapi_key=%s" % (url, TMDB_KEY)
    global base_url
    global poster_size
    global fanart_size
    if not base_url:
        base_url = True
        base_url, poster_size, fanart_size = get_tmdb_config()
    return get_JSON_response(url, cache_days, "TheMovieDB")


def get_tmdb_config():
    return ("http://image.tmdb.org/t/p/", "w500", "w1280")
    response = get_tmdb_data("configuration?", 60)
    # prettyprint(response)
    if response:
        return (response["images"]["base_url"], response["images"]["POSTER_SIZES"][-2], response["images"]["BACKDROP_SIZES"][-2])
    else:
        return ("", "", "")


def get_company_data(company_id):
    response = get_tmdb_data("company/%s/movies?append_to_response=movies&" % (company_id), 30)
    if response and "results" in response:
        return handle_tmdb_movies(response["results"])
    else:
        return []


def GetCreditInfo(credit_id):
    response = get_tmdb_data("credit/%s?language=%s&" % (str(credit_id), ADDON.getSetting("LanguageID")), 30)
    prettyprint(response)
    # if response and "results" in response:
    #     return handle_tmdb_movies(response["results"])
    # else:
    #     return []


def GetSeasonInfo(tmdb_tvshow_id, tvshowname, season_number):
    if not tmdb_tvshow_id:
        response = get_tmdb_data("search/tv?query=%s&language=%s&" % (url_quote(tvshowname), ADDON.getSetting("LanguageID")), 30)
        if response["results"]:
            tmdb_tvshow_id = str(response['results'][0]['id'])
        else:
            tvshowname = re.sub('\(.*?\)', '', tvshowname)
            response = get_tmdb_data("search/tv?query=%s&language=%s&" % (url_quote(tvshowname), ADDON.getSetting("LanguageID")), 30)
            if response["results"]:
                tmdb_tvshow_id = str(response['results'][0]['id'])
    response = get_tmdb_data("tv/%s/season/%s?append_to_response=videos,images,external_ids,credits&language=%s&include_image_language=en,null,%s&" % (tmdb_tvshow_id, season_number, ADDON.getSetting("LanguageID"), ADDON.getSetting("LanguageID")), 7)
    # prettyprint(response)
    if not response:
        notify("Could not find season info")
        return None
    videos = []
    backdrops = []
    if ("poster_path" in response) and (response["poster_path"]):
        poster_path = base_url + poster_size + response['poster_path']
        poster_path_small = base_url + "w342" + response['poster_path']
    else:
        poster_path = ""
        poster_path_small = ""
    if response.get("name", False):
        Title = response["name"]
    elif season_number == "0":
        Title = "Specials"
    else:
        Title = "Season %s" % season_number
    season = {'SeasonDescription': clean_text(response["overview"]),
              'Plot': clean_text(response["overview"]),
              'TVShowTitle': tvshowname,
              'Thumb': poster_path_small,
              'Poster': poster_path,
              'Title': Title,
              'ReleaseDate': response["air_date"],
              'AirDate': response["air_date"]}
    if "videos" in response:
        videos = handle_tmdb_videos(response["videos"]["results"])
    if "backdrops" in response["images"]:
        backdrops = HandleTMDBPeopleImagesResult(response["images"]["backdrops"])
    answer = {"general": season,
              "actors": handle_tmdb_people(response["credits"]["cast"]),
              "crew": handle_tmdb_people(response["credits"]["crew"]),
              "videos": videos,
              "episodes": handle_tmdb_episodes(response["episodes"]),
              "images": HandleTMDBPeopleImagesResult(response["images"]["posters"]),
              "backdrops": backdrops}
    return answer


def get_movie_tmdb_id(imdb_id=None, name=None, dbid=None):
    if dbid and (int(dbid) > 0):
        movie_id = get_imdb_id_from_db("movie", dbid)
        log("IMDB Id from local DB:" + str(movie_id))
        return movie_id
    elif imdb_id:
        response = get_tmdb_data("find/tt%s?external_source=imdb_id&language=%s&" % (imdb_id.replace("tt", ""), ADDON.getSetting("LanguageID")), 30)
        return response["movie_results"][0]["id"]
    elif name:
        return search_media(name)
    else:
        return None


def get_show_tmdb_id(tvdb_id=None, source="tvdb_id"):
    response = get_tmdb_data("find/%s?external_source=%s&language=%s&" % (tvdb_id, source, ADDON.getSetting("LanguageID")), 30)
    try:
        return response["tv_results"][0]["id"]
    except:
        notify("TVShow Info not available.")
        return None


def GetTrailer(movieid=None):
    response = get_tmdb_data("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                             (movieid, ADDON.getSetting("LanguageID"), ADDON.getSetting("LanguageID")), 30)
    if response and "videos" in response and response['videos']['results']:
        youtube_id = response['videos']['results'][0]['key']
        return youtube_id
    notify("Could not get trailer")
    return ""


def extended_movie_info(movieid=None, dbid=None, cache_time=14):
    if checkLogin():
        session_string = "session_id=%s&" % (get_session_id())
    else:
        session_string = ""
    response = get_tmdb_data("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&%s" %
                             (movieid, ADDON.getSetting("LanguageID"), ADDON.getSetting("LanguageID"), session_string), cache_time)
    # prettyprint(response)
    authors = []
    directors = []
    year = ""
    mpaa = ""
    SetName = ""
    SetID = ""
    poster_path = ""
    poster_path_small = ""
    backdrop_path = ""
    if not response:
        notify("Could not get movie information")
        return {}
    genres = [item["name"] for item in response["genres"]]
    Studio = [item["name"] for item in response["production_companies"]]
    for item in response['credits']['crew']:
        if item["job"] == "Author":
            authors.append(item["name"])
        elif item["job"] == "Director":
            directors.append(item["name"])
    if response['releases']['countries']:
        mpaa = response['releases']['countries'][0]['certification']
    Set = fetch(response, "belongs_to_collection")
    if Set:
        SetName = fetch(Set, "name")
        SetID = fetch(Set, "id")
    if 'release_date' in response and fetch(response, 'release_date'):
        year = fetch(response, 'release_date')[:4]
    if ("backdrop_path" in response) and (response["backdrop_path"]):
        backdrop_path = base_url + fanart_size + response['backdrop_path']
    if ("poster_path" in response) and (response["poster_path"]):
        poster_path = base_url + "original" + response['poster_path']
        poster_path_small = base_url + "w342" + response['poster_path']
    path = 'plugin://script.extendedinfo/?info=youtubevideo&&id=%s' % str(fetch(response, "id"))
    movie = {'Art(fanart)': backdrop_path,
             'Art(poster)': poster_path,
             'Thumb': poster_path_small,
             'Poster': poster_path,
             'fanart': backdrop_path,
             'Title': fetch(response, 'title'),
             'Label': fetch(response, 'title'),
             'Tagline': fetch(response, 'tagline'),
             'duration': fetch(response, 'runtime'),
             'duration(h)': format_time(fetch(response, 'runtime'), "h"),
             'duration(m)': format_time(fetch(response, 'runtime'), "m"),
             'mpaa': mpaa,
             'Director': " / ".join(directors),
             'Writer': " / ".join(authors),
             'Budget': millify(fetch(response, 'budget')),
             'Revenue': millify(fetch(response, 'revenue')),
             'Homepage': fetch(response, 'homepage'),
             'Set': SetName,
             'SetId': SetID,
             'ID': fetch(response, 'id'),
             'imdb_id': fetch(response, 'imdb_id'),
             'Plot': clean_text(fetch(response, 'overview')),
             'OriginalTitle': fetch(response, 'original_title'),
             'Country': fetch(response, 'original_language'),
             'Genre': " / ".join(genres),
             'Rating': fetch(response, 'vote_average'),
             'Votes': fetch(response, 'vote_count'),
             'Adult': str(fetch(response, 'adult')),
             'Popularity': fetch(response, 'popularity'),
             'Status': fetch(response, 'status'),
             'Path': path,
             'ReleaseDate': fetch(response, 'release_date'),
             'Premiered': fetch(response, 'release_date'),
             'Studio': " / ".join(Studio),
             'Year': year}
    if "videos" in response:
        videos = handle_tmdb_videos(response["videos"]["results"])
    else:
        videos = []
    if "account_states" in response:
        account_states = response["account_states"]
    else:
        account_states = None
    synced_movie = compare_with_library([movie])
    if synced_movie:
        answer = {"general": synced_movie[0],
                  "actors": handle_tmdb_people(response["credits"]["cast"]),
                  "similar": handle_tmdb_movies(response["similar"]["results"]),
                  "lists": handle_tmdb_misc(response["lists"]["results"]),
                  "studios": handle_tmdb_misc(response["production_companies"]),
                  "releases": handle_tmdb_misc(response["releases"]["countries"]),
                  "crew": handle_tmdb_people(response["credits"]["crew"]),
                  "genres": handle_tmdb_misc(response["genres"]),
                  "keywords": handle_tmdb_misc(response["keywords"]["keywords"]),
                  "reviews": handle_tmdb_misc(response["reviews"]["results"]),
                  "videos": videos,
                  "account_states": account_states,
                  "images": HandleTMDBPeopleImagesResult(response["images"]["posters"]),
                  "backdrops": HandleTMDBPeopleImagesResult(response["images"]["backdrops"])}
    else:
        answer = []
    return answer


def extended_tvshow_info(tvshow_id=None, cache_time=7):
    session_string = ""
    if checkLogin():
        session_string = "session_id=%s&" % (get_session_id())
    response = get_tmdb_data("tv/%s?append_to_response=account_states,alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,translations,videos&language=%s&include_image_language=en,null,%s&%s" %
                             (str(tvshow_id), ADDON.getSetting("LanguageID"), ADDON.getSetting("LanguageID"), session_string), cache_time)
    if not response:
        return False
    videos = []
    if "account_states" in response:
        account_states = response["account_states"]
    else:
        account_states = None
    if "videos" in response:
        videos = handle_tmdb_videos(response["videos"]["results"])
    tmdb_id = fetch(response, 'id')
    poster_path = ""
    backdrop_path = ""
    if ("backdrop_path" in response) and (response["backdrop_path"]):
        backdrop_path = base_url + fanart_size + response['backdrop_path']
    if ("poster_path" in response) and (response["poster_path"]):
        poster_path = base_url + "original" + response['poster_path']
    if len(response.get("episode_run_time", -1)) > 1:
        duration = "%i - %i" % (min(response["episode_run_time"]), max(response["episode_run_time"]))
    elif len(response.get("episode_run_time", -1)) == 1:
        duration = "%i" % (response["episode_run_time"][0])
    else:
        duration = ""
    release_date = fetch(response, 'first_air_date')
    if release_date:
        year = release_date[:4]
    else:
        year = ""
    genres = [item["name"] for item in response["genres"]]
    newtv = {'Art(fanart)': backdrop_path,
             'Art(poster)': poster_path,
             'Thumb': poster_path,
             'Poster': poster_path,
             'fanart': backdrop_path,
             'Title': fetch(response, 'name'),
             'TVShowTitle': fetch(response, 'name'),
             'OriginalTitle': fetch(response, 'original_name'),
             'duration': duration,
             'duration(h)': format_time(duration, "h"),
             'duration(m)': format_time(duration, "m"),
             'ID': tmdb_id,
             'Genre': " / ".join(genres),
             'credit_id': fetch(response, 'credit_id'),
             'Plot': clean_text(fetch(response, "overview")),
             'year': year,
             'media_type': "tv",
             'Path': 'plugin://script.extendedinfo/?info=action&&id=RunScript(script.extendedinfo,info=extendedtvinfo,id=%s)' % tmdb_id,
             'Rating': fetch(response, 'vote_average'),
             'User_Rating': str(fetch(response, 'rating')),
             'Votes': fetch(response, 'vote_count'),
             'Status': fetch(response, 'status'),
             'ShowType': fetch(response, 'type'),
             'homepage': fetch(response, 'homepage'),
             'last_air_date': fetch(response, 'last_air_date'),
             'first_air_date': release_date,
             'number_of_episodes': fetch(response, 'number_of_episodes'),
             'number_of_seasons': fetch(response, 'number_of_seasons'),
             'in_production': fetch(response, 'in_production'),
             'Release_Date': release_date,
             'ReleaseDate': release_date,
             'Premiered': release_date}
    answer = {"general": newtv,
              "actors": handle_tmdb_people(response["credits"]["cast"]),
              "similar": handle_tmdb_tvshows(response["similar"]["results"]),
              "studios": handle_tmdb_misc(response["production_companies"]),
              "networks": handle_tmdb_misc(response["networks"]),
              "certifications": handle_tmdb_misc(response["content_ratings"]["results"]),
              "crew": handle_tmdb_people(response["credits"]["crew"]),
              "genres": handle_tmdb_misc(response["genres"]),
              "keywords": handle_tmdb_misc(response["keywords"]["results"]),
              "videos": videos,
              "account_states": account_states,
              "seasons": handle_tmdb_seasons(response["seasons"]),
              "images": HandleTMDBPeopleImagesResult(response["images"]["posters"]),
              "backdrops": HandleTMDBPeopleImagesResult(response["images"]["backdrops"])}
    return answer


def extended_episode_info(tvshow_id, season, episode, cache_time=7):
    if not season:
        season = 0
    session_string = ""
    if checkLogin():
        session_string = "session_id=%s&" % (get_session_id())
    response = get_tmdb_data("tv/%s/season/%s/episode/%s?append_to_response=account_states,credits,external_ids,images,rating,videos&language=%s&include_image_language=en,null,%s&%s&" %
                             (str(tvshow_id), str(season), str(episode), ADDON.getSetting("LanguageID"), ADDON.getSetting("LanguageID"), session_string), cache_time)
    videos = []
    # prettyprint(response)
    if "videos" in response:
        videos = handle_tmdb_videos(response["videos"]["results"])
    if "account_states" in response:
        account_states = response["account_states"]
    else:
        account_states = None
    answer = {"general": handle_tmdb_episodes([response])[0],
              "actors": handle_tmdb_people(response["credits"]["cast"]),
              "account_states": account_states,
              "crew": handle_tmdb_people(response["credits"]["crew"]),
              # "genres": handle_tmdb_misc(response["genres"]),
              "videos": videos,
              # "seasons": handle_tmdb_seasons(response["seasons"]),
              "images": HandleTMDBPeopleImagesResult(response["images"]["stills"])}
    return answer


def GetExtendedActorInfo(actorid):
    response = get_tmdb_data("person/%s?append_to_response=tv_credits,movie_credits,combined_credits,images,tagged_images&" % (actorid), 1)
    tagged_images = []
    if "tagged_images" in response:
        tagged_images = HandleTMDBPeopleTaggedImagesResult(response["tagged_images"]["results"])
    answer = {"general": handle_tmdb_people([response])[0],
              "movie_roles": handle_tmdb_movies(response["movie_credits"]["cast"]),
              "tvshow_roles": handle_tmdb_tvshows(response["tv_credits"]["cast"]),
              "movie_crew_roles": handle_tmdb_movies(response["movie_credits"]["crew"]),
              "tvshow_crew_roles": handle_tmdb_tvshows(response["tv_credits"]["crew"]),
              "tagged_images": tagged_images,
              "images": HandleTMDBPeopleImagesResult(response["images"]["profiles"])}
    return answer


def get_movie_lists(list_id):
    response = get_tmdb_data("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                             (list_id, ADDON.getSetting("LanguageID"), ADDON.getSetting("LanguageID")), 5)
    return handle_tmdb_misc(response["lists"]["results"])


def get_rated_media_items(media_type):
    '''takes "tv/episodes", "tv" or "movies"'''
    if checkLogin():
        session_id = get_session_id()
        account_id = get_account_info()
        response = get_tmdb_data("account/%s/rated/%s?session_id=%s&language=%s&" % (str(account_id), media_type, str(session_id), ADDON.getSetting("LanguageID")), 0)
    else:
        session_id = get_guest_session_id()
        response = get_tmdb_data("guest_session/%s/rated_movies?language=%s&" % (str(session_id), ADDON.getSetting("LanguageID")), 0)
    if media_type == "tv/episodes":
        return handle_tmdb_episodes(response["results"])
    elif media_type == "tv":
        return handle_tmdb_tvshows(response["results"], False, None)
    else:
        return handle_tmdb_movies(response["results"], False, None)


def get_fav_items(media_type):
    '''takes "tv/episodes", "tv" or "movies"'''
    session_id = get_session_id()
    account_id = get_account_info()
    response = get_tmdb_data("account/%s/favorite/%s?session_id=%s&language=%s&" % (str(account_id), media_type, str(session_id), ADDON.getSetting("LanguageID")), 0)
    if "results" in response:
        if media_type == "tv":
            return handle_tmdb_tvshows(response["results"], False, None)
        elif media_type == "tv/episodes":
            return handle_tmdb_episodes(response["results"])
        else:
            return handle_tmdb_movies(response["results"], False, None)
    else:
        return []


def get_movies_from_list(list_id, cache_time=5):
    response = get_tmdb_data("list/%s?language=%s&" % (str(list_id), ADDON.getSetting("LanguageID")), cache_time)
    #  prettyprint(response)
    return handle_tmdb_movies(response["items"], False, None)


def GetPopularActorList():
    response = get_tmdb_data("person/popular?", 1)
    return handle_tmdb_people(response["results"])


def GetActorMovieCredits(actor_id):
    response = get_tmdb_data("person/%s/movie_credits?" % (actor_id), 1)
    return handle_tmdb_movies(response["cast"])


def GetActorTVShowCredits(actor_id):
    response = get_tmdb_data("person/%s/tv_credits?" % (actor_id), 1)
    return handle_tmdb_movies(response["cast"])


def GetMovieKeywords(movie_id):
    response = get_tmdb_data("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                             (movie_id, ADDON.getSetting("LanguageID"), ADDON.getSetting("LanguageID")), 30)
    keywords = []
    if "keywords" in response:
        for keyword in response["keywords"]["keywords"]:
            keyword_dict = {'id': fetch(keyword, 'id'),
                            'name': keyword['name']}
            keywords.append(keyword_dict)
        return keywords
    else:
        log("No keywords in JSON answer")
        return []


def get_similar_movies(movie_id):
    response = get_tmdb_data("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                             (movie_id, ADDON.getSetting("LanguageID"), ADDON.getSetting("LanguageID")), 10)
    if "similar" in response:
        return handle_tmdb_movies(response["similar"]["results"])
    else:
        log("No JSON Data available")


def get_similar_tvshows(tvshow_id):
    session_string = ""
    if checkLogin():
        session_string = "session_id=%s&" % (get_session_id())
    response = get_tmdb_data("tv/%s?append_to_response=account_states,alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,translations,videos&language=%s&include_image_language=en,null,%s&%s" %
                             (str(tvshow_id), ADDON.getSetting("LanguageID"), ADDON.getSetting("LanguageID"), session_string), 10)
    if "similar" in response:
        return handle_tmdb_tvshows(response["similar"]["results"])
    else:
        log("No JSON Data available")


def GetMovieDBTVShows(tvshow_type):
    response = get_tmdb_data("tv/%s?language=%s&" % (tvshow_type, ADDON.getSetting("LanguageID")), 0.3)
    if "results" in response:
        return handle_tmdb_tvshows(response["results"], False, None)
    else:
        log("No JSON Data available for GetMovieDBTVShows(%s)" % tvshow_type)
        log(response)


def GetMovieDBMovies(movie_type):
    response = get_tmdb_data("movie/%s?language=%s&" % (movie_type, ADDON.getSetting("LanguageID")), 0.3)
    if "results" in response:
        return handle_tmdb_movies(response["results"], False, None)
    else:
        log("No JSON Data available for GetMovieDBMovies(%s)" % movie_type)
        log(response)


def GetSetMovies(set_id):
    response = get_tmdb_data("collection/%s?language=%s&append_to_response=images&include_image_language=en,null,%s&" % (set_id, ADDON.getSetting("LanguageID"), ADDON.getSetting("LanguageID")), 14)
    if response:
        backdrop_path = ""
        poster_path = ""
        small_poster_path = ""
        if ("backdrop_path" in response) and (response["backdrop_path"]):
            backdrop_path = base_url + fanart_size + response['backdrop_path']
        if ("poster_path" in response) and (response["poster_path"]):
            poster_path = base_url + "original" + response['poster_path']
            small_poster_path = base_url + "w342" + response["poster_path"]
        info = {"label": response["name"],
                "Poster": poster_path,
                "Thumb": small_poster_path,
                "Fanart": backdrop_path,
                "overview": response["overview"],
                "ID": response["id"]}
        return handle_tmdb_movies(response.get("parts", [])), info
    else:
        log("No JSON Data available")
        return [], {}


def GetDirectorMovies(person_id):
    response = get_tmdb_data("person/%s/credits?language=%s&" % (person_id, ADDON.getSetting("LanguageID")), 14)
    # return handle_tmdb_movies(response["crew"]) + handle_tmdb_movies(response["cast"])
    if "crew" in response:
        return handle_tmdb_movies(response["crew"])
    else:
        log("No JSON Data available")


def search_media(media_name=None, year='', media_type="movie"):
    log('TMDB API search criteria: Title[''%s''] | Year[''%s'']' % (media_name, year))
    media_name_url = url_quote(media_name)
    if media_name_url:
        response = get_tmdb_data("search/%s?query=%s+%s&language=%s&include_adult=%s&" % (media_type, media_name_url, year, ADDON.getSetting("LanguageID"), include_adult), 1)
        try:
            if not response == "Empty":
                for item in response['results']:
                    if item['id']:
                        return item['id']
        except Exception as e:
            log(e)


class Get_Youtube_Vids_Thread(threading.Thread):

    def __init__(self, search_string="", hd="", order="relevance", limit=15):
        threading.Thread.__init__(self)
        self.search_string = search_string
        self.hd = hd
        self.order = order
        self.limit = limit

    def run(self):
        self.listitems = get_youtube_search_videos(self.search_string, self.hd, self.order, self.limit)
