# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import urllib.request, urllib.parse, urllib.error
import re

from kutils import utils
from kutils import ItemList
from kutils.abs_last_fm import AbstractLastFM


class LastFM(AbstractLastFM):
    LAST_FM_API_KEY = 'd942dd5ca4c9ee5bd821df58cf8130d4'
    GOOGLE_MAPS_KEY = 'AIzaSyBESfDvQgWtWLkNiOYXdrA9aU-2hv_eprY'
    BASE_URL = 'http://ws.audioscrobbler.com/2.0/?'

    @classmethod
    def handle_albums(cls, results):
        albums = ItemList(content_type="albums")
        if not results:
            return albums
        if 'topalbums' in results and "album" in results['topalbums']:
            for album in results['topalbums']['album']:
                albums.append({'artist': album['artist']['name'],
                               'mbid': album.get('mbid', ""),
                               'mediatype': "album",
                               'thumb': album['image'][-1]['#text'],
                               'label': "%s - %s" % (album['artist']['name'], album['name']),
                               'title': album['name']})
                albums.append(album)
        return albums

    @classmethod
    def handle_artists(cls, results):
        artists = ItemList(content_type="artists")
        if not results:
            return artists
        for artist in results['artist']:
            if 'name' not in artist:
                continue
            artist = {'title': artist['name'],
                      'label': artist['name'],
                      'mediatype': "artist",
                      'mbid': artist.get('mbid'),
                      'thumb': artist['image'][-1]['#text'],
                      'Listeners': format(int(artist.get('listeners', 0)), ",d")}
            artists.append(artist)
        return artists

    @classmethod
    def get_top_artists(cls):
        results = cls.get_data(method="Chart.getTopArtists",
                           params={"limit": "100"})
        return cls.handle_artists(results['artists'])

    @classmethod
    def get_artist_albums(cls, artist_mbid):
        if not artist_mbid:
            return ItemList(content_type="albums")
        results = cls.get_data(method="Artist.getTopAlbums",
                           params={"mbid": artist_mbid})
        return cls.handle_albums(results)

    @classmethod
    def get_similar_artists(cls, artist_mbid):
        if not artist_mbid:
            return ItemList(content_type="artists")
        params = {"mbid": artist_mbid,
                  "limit": "400"}
        results = cls.get_data(method="Artist.getSimilar",
                           params=params)
        if results and "similarartists" in results:
            return cls.handle_artists(results['similarartists'])

    @classmethod
    def get_track_info(cls, artist_name="", track=""):
        if not artist_name or not track:
            return {}
        params = {"artist": artist_name,
                  "track": track}
        results = cls.get_data(method="track.getInfo",
                               params=params)
        if not results:
            return {}
        summary = results['track']['wiki']['summary'] if "wiki" in results['track'] else ""
        return {'playcount': str(results['track']['playcount']),
                'thumb': str(results['track']['playcount']),
                'summary': cls.clean_text(summary)}

    @classmethod
    def get_data(cls, method, params=None, cache_days=0.5):
        params = params if params else {}
        params["method"] = method
        params["api_key"] = cls.LAST_FM_API_KEY
        params["format"] = "json"
        params = {k: str(v) for k, v in params.items() if v}
        url = "{base_url}{params}".format(base_url=cls.BASE_URL,
                                          params=urllib.parse.urlencode(params))
        return utils.get_JSON_response(url=url,
                                       cache_days=cache_days,
                                       folder="LastFM")

    @classmethod
    def clean_text(cls, text):
        if not text:
            return ""
        text = re.sub(r'(From Wikipedia, the free encyclopedia)|(Description above from the Wikipedia.*?Wikipedia)', '', text)
        text = re.sub(r'<(.|\n|\r)*?>', '', text)
        text = text.replace('<br />', '[CR]')
        text = text.replace('<em>', '[I]').replace('</em>', '[/I]')
        text = text.replace('&amp;', '&')
        text = text.replace('&gt;', '>').replace('&lt;', '<')
        text = text.replace('&#39;', "'").replace('&quot;', '"')
        text = re.sub(r'\n\\.$', "", text)
        text = text.replace('User-contributed text is available under the Creative Commons By-SA License and may also be available under the GNU FDL.', '')
        removals = {'\u200b', " ", "\n"}
        while text:
            s = text[0]
            e = text[-1]
            if s in removals:
                text = text[1:]
            elif e in removals:
                text = text[:-1]
            elif s.startswith(".") and not s.startswith(".."):
                text = text[1:]
            else:
                break
        return text.strip()
