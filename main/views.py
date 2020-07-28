from django.shortcuts import render
import os
import time
from collections import OrderedDict
from pymongo import MongoClient, DESCENDING, ASCENDING
from dateutil import parser
import urllib.parse


MONGODB_URI = os.environ.get("MONGODB_URI")

client = MongoClient(MONGODB_URI)
db = client.get_default_database()
db_nowplaying = db["thehighway_nowplaying"]
db_songs = db["thehighway_songs"]
ONE_DAY_SECONDS = 60 * 60 * 24


# Now Playing Page View (Index)
def now_playing(request, page):
    songs = get_now_playing(page)
    song_dict = OrderedDict()
    song_id = 1
    for song in songs:
        song_dict[song_id] = song
        song_dict[song_id]["timeago"] = get_time_ago_string(song["start_time"] / 1000)
        song_dict[song_id]["ytlink"] = get_youtube_link(song)
        song_id += 1
    song_dict["page"] = page
    song_dict["dayTotal"] = get_day_total()
    song_dict["dayUniqueTotal"] = get_day_unique_total()
    return render(request, "main/nowplaying.html", {"songs": song_dict})


# Most Played Last Day Page
def most_played_day(request):
    songs = get_most_played_since(1)
    songList = []
    for song in songs:
        song["ytlink"] = get_youtube_link(song)
        songList.append(song)
    return render(request, "main/mostplayed-day.html", {"songs": songList})


# Most Played Last Week Page
def most_played_week(request):
    songs = get_most_played_since(7)
    songList = []
    for song in songs:
        song["ytlink"] = get_youtube_link(song)
        songList.append(song)
    return render(request, "main/mostplayed-week.html", {"songs": songList})


# Most Played Last Month Page
def most_played_month(request):
    songs = get_most_played_since(30)
    songList = []
    for song in songs:
        song["ytlink"] = get_youtube_link(song)
        songList.append(song)
    return render(request, "main/mostplayed-month.html", {"songs": songList})


# Artists Page
def artists(request):
    return render(request, "main/artists.html")


# Song Details Page
def song(request):
    artist = request.GET.get("artist")
    title = request.GET.get("title")
    song_data = {}

    if (artist is not None) and (title is not None):
        played_daily_stats = get_played_daily(artist, title)
        chart_data = prepare_gcharts_data(played_daily_stats)
        song_result = get_song(artist, title)
        if song_result is not None:
            song_data = song_result
            song_data["chartdata"] = chart_data
            song_data["ytlink"] = get_youtube_link(song_data)

    return render(request, "main/song.html", {"song": song_data})


# New Songs Page
def new(request):
    songs = db_songs.find({}).sort("first_heard", direction=DESCENDING).limit(100)
    songList = []
    for song in songs:
        song["ytlink"] = get_youtube_link(song)
        songList.append(song)
    return render(request, "main/new.html", {"songs": songList})


# About Page
def about(request):
    return render(request, "main/about.html")


def get_now_playing(page):
    skip = int(page) - 1
    songs = db_nowplaying.find({}).sort("start_time", direction=DESCENDING).limit(16).skip((skip * 16))
    return songs


def get_time_ago_string(song_time):
    delta_seconds = time.time() - song_time
    m, s = divmod(delta_seconds, 60)
    h, m = divmod(m, 60)

    time_ago = ""
    if h > 0:
        if h == 1:
            time_ago += "1 hour ago"
            return time_ago
        else:
            time_ago += str(round(h))
            time_ago += " hours ago"
            return time_ago
    if m > 0:
        if m == 0:
            time_ago += "1 minute ago"
            return time_ago
        else:
            time_ago += str(round(m))
            time_ago += " minutes ago"
            return time_ago
    if s > 0:
        time_ago += str(round(s))
        time_ago += " seconds ago"
        return time_ago


def get_youtube_link(song_json):
    yt_link = "https://www.youtube.com/results?search_query="

    artist = str(song_json["artist"])
    srch_song = str(song_json["title"])
    srch_artist = artist.replace("/", " ")

    yt_link += urllib.parse.quote_plus(srch_artist)
    yt_link += "+"
    yt_link += urllib.parse.quote_plus(srch_song)
    return yt_link


def get_day_total():
    now = time.time()
    # Match data epoch timestamp units
    one_day_ago = int(now - ONE_DAY_SECONDS) * 1000
    day_total = db_nowplaying.find({"start_time": {"$gte": one_day_ago}}).count()
    return day_total


def get_day_unique_total():
    now = time.time()
    # Match data epoch timestamp units
    one_day_ago = int(now - ONE_DAY_SECONDS) * 1000
    day_unique_cursor = db_nowplaying.find({"start_time": {"$gte": one_day_ago}}).distinct("title")
    day_unique_total = len(day_unique_cursor)
    return day_unique_total


def get_most_played_since(days_ago):
    now = time.time()
    # Match data epoch timestamp units
    time_ago = int((now - (days_ago * ONE_DAY_SECONDS)) * 1000)
    query = [{"$project": {"start_time": 1,
                           "artist": 1,
                           "title": 1,
                           "spotify": 1}},
             {"$match": {"start_time": {"$gt": time_ago}}},
             {"$group": {"_id": {"artist": "$artist", "title": "$title"},
                         "artist": {"$first": "$artist"},
                         "title": {"$first": "$title"},
                         "spotify": {"$first": "$spotify"},
                         "num_plays": {"$sum": 1}
                         }},
             {"$sort": {"num_plays": DESCENDING}},
             {"$limit": 100}]
    popular = db_nowplaying.aggregate(query)
    return popular


# Get played count per day in the specified timezone offset.
def get_played_daily(artist, title):
    query = [{"$project": {"start_time_date": {"$toDate": "$start_time"},
                           "artist": 1,
                           "title": 1,
                           "album": 1}},
                           # "spotify": 1}},
             {"$match": {"artist": str(artist), "title": str(title)}},
             {"$group": {"_id": {
                            "year": {"$year": "$start_time_date"},
                            "month": {"$month": "$start_time_date"},
                            "day": {"$dayOfMonth": "$start_time_date"}},
                         "artist": {"$first": "$artist"},
                         "title": {"$first": "$title"},
                         # "spotify": {"$first": "$spotify"},
                         "num_plays": {"$sum": 1},
                         "ondate": {"$first": "$start_time_date"}}},
             {"$sort": {"ondate": ASCENDING}}]
    daily_played = db_nowplaying.aggregate(query)
    return daily_played


def prepare_gcharts_data(songs):
    fulldata = ""
    for song in songs:
        # Hack to prepare Google charts data
        year = parser.parse(str(song["ondate"])).strftime("%Y")
        month = str(int(parser.parse(str(song["ondate"])).strftime("%m")) - 1)
        day = parser.parse(str(song["ondate"])).strftime("%d")
        date = "new Date(" + year + ", " + month + ", " + day + ")"
        fulldata += "[" + date + ", " + str(song["num_plays"]) + "],\n"
    return fulldata


def get_song(artist, title):
    song_info = None
    song_result = db_songs.find({"artist": artist, "title": title})
    if song_result.count() > 0:
        song_info = song_result.next()
        first_heard = song_info["first_heard"]
        last_heard = song_info["last_heard"]
        song_info["first_heard"] = time.strftime("%b %d %Y, %H:%M:%S %Z", time.gmtime(first_heard/1000))
        song_info["last_heard"] = time.strftime("%b %d %Y, %H:%M:%S %Z", time.gmtime(last_heard/1000))
    return song_info
