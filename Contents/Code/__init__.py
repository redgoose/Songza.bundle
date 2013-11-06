import time
import urllib

ART = 'art-default.jpg'
ICON = 'icon-default.png'
SONGZA_API = 'http://songza.com/api/1/'

PLAYLIST_LENGTH = 10
PLAYLIST_RESET_INTERVAL = 600

def Start():

    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = 'Songza'
    
    DirectoryObject.thumb = R(ICON)

    HTTP.CacheTime = 0
    Dict['Songza'] = {}

    if 'Songza' not in Dict:
        Dict['Songza'] = {}

    Dict['Songza']['station_id'] = ''
    Dict['Songza']['timestamp'] = 0

@handler("/music/songza", "Songza")
def MainMenu():
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(SituationsList), title=L('Music Concierge')))
    return oc

@route("/music/songza/situations")
def SituationsList():

    current_date = Datetime.Now().strftime('%Y-%m-%dT%H:%M:%S+00:00')
    period = ((Datetime.Now().hour / 4) - 1) % 6
    if period == 5:
        day = Datetime.Now().isoweekday() - 1 # If period is late night, then set day to yesterday
    else:
        day = Datetime.Now().isoweekday() % 7

    url = SONGZA_API + 'situation/targeted?site=songza&'
    params = urllib.urlencode({
        'current_date': current_date,
        'day': day,
        'period': period,
        'device': 'web',
    })
    
    url = url + params
    situations = JSON.ObjectFromURL(url)

    oc = ObjectContainer(title2=L('Pick a situation'))
    for s in situations:
        oc.add(DirectoryObject(
            key = Callback(SubSituationsList, situations=s['situations']),
            title = s['title']))
    return oc

@route("/music/songza/subsituations", situations=dict)
def SubSituationsList(situations):
    oc = ObjectContainer(title2=L('Pick a category'))

    for s in situations:
        oc.add(DirectoryObject(
            key = Callback(StationList, station_ids=s['station_ids']),
            title = s['title']))
    return oc

@route("/music/songza/stations", station_ids=dict)
def StationList(station_ids):

    keys = []
    for i in range(len(station_ids)):
        keys.append('id')
    ids = zip(keys, station_ids)
    params = urllib.urlencode(ids)

    url = SONGZA_API + 'station/multi?' + params
    stations = JSON.ObjectFromURL(url)

    oc = ObjectContainer(title2=L('Select a station'))

    for s in stations:
        oc.add(DirectoryObject(
            key = Callback(Station, station=s),
            title = s['name']))
    
    return oc

@route("/music/songza/station", station=dict)
def Station(station):
    title2 = station['name']
    station_id = str(station['id'])
    playlist_stale = False
    
    if Dict['Songza']['timestamp'] + PLAYLIST_RESET_INTERVAL < int(Datetime.TimestampFromDatetime(Datetime.Now())):
        playlist_stale = True

    if Dict['Songza']['station_id'] != station_id or playlist_stale:
        Dict['Songza']['station_id'] = station_id
        Dict['Songza']['timestamp'] = int(Datetime.TimestampFromDatetime(Datetime.Now()))
        Dict['Songza']['playlist'] = []

    while len(Dict['Songza']['playlist']) < PLAYLIST_LENGTH:
        next_track_url = SONGZA_API + 'station/' + station_id + '/next'
        track = JSON.ObjectFromURL(next_track_url)
        
        song = {
            'url': track['listen_url'],
            'artist': track['song']['artist']['name'],
            'song_title': track['song']['title'],
            'album': track['song']['album'],
            'thumb': track['song']['cover_url']
        }
        Dict['Songza']['playlist'].append(song)
        Dict['Songza']['timestamp'] = int(Datetime.TimestampFromDatetime(Datetime.Now()))
        time.sleep(1) # 1sec between calls so we don't get blocked/limited
    
    oc = ObjectContainer(title2=title2, no_cache=True)
    
    for song in Dict['Songza']['playlist']:
        track = GetTrack(song)
        oc.add(track)
    
    return oc

@route("/music/songza/track", song=dict)
def GetTrack(song):
    
    items = []
    items.insert(0, MediaObject(
        parts = [PartObject(key=Callback(PlayAudio, url=song['url'], ext='aac', song=song))],
        container = Container.MP4,
        audio_codec = AudioCodec.AAC,
        audio_channels = 2
    ))

    track = TrackObject(
        key = Callback(GetTrack, song=song),
        rating_key = song['url'],
        title = song['song_title'],
        album = song['album'],
        artist = song['artist'],
        thumb = song['thumb'],
        items = items
    )

    return track

def PlayAudio(url, ext=None, song=None):
    try:
        Dict['Songza']['playlist'].remove(song)
    except:
        pass
    return Redirect(url) 
