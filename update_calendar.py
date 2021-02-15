import re
# BeautifulSoup
from bs4 import BeautifulSoup as soup
from urllib.request import Request, urlopen as uReq
# Google Calendar
import pickle
import os.path
from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

kpopUrl = "http://www.kpopmap.com/update-upcoming-k-pop-comeback-debut-lineup-in-february-2021/"
kpopCalId = ''
kdramaUrl = "https://wiki.d-addicts.com/Upcoming_KDrama"
kdramaCalId = 'p030obls0j9ghhgf6u79qbjrts@group.calendar.google.com'
SCOPES = ['https://www.googleapis.com/auth/calendar']

def makeSoup(url):
    uClient = uReq(url)
    pageSoup = soup(uClient.read(), "html.parser")
    uClient.close()
    return pageSoup

def updateKdrama(service):
    soup = makeSoup(kdramaUrl)
    kdramaSchedule = soup.find("div", "mw-parser-output").contents

    for elem in kdramaSchedule[6::]:
        if elem.name == 'table':
            populateKdramaCal(service, elem.tbody.contents)

def updateKpop(service):
    soup = makeSoup(kpopUrl)
    cbSchedule = soup.find("div", "comeback-schedule")

def populateKdramaCal(service, dramas):
    for drama in dramas[2::2]:
        dramaContent = drama.contents
        title = dramaContent[1].text
        wiki = 'https://wiki.d-addicts.com' + dramaContent[1].a['href']
        date = dramaContent[3].text
        cast = dramaContent[5].text
        # Premiere date is not set yet
        if len(date) < 12:
            break
        # Wiki page has not been made yet
        if len(dramaContent[1].a['href']) > len(title):
            continue
        network, recurrence = getDramaInfo(wiki)
        # Doesn't follow the pattern
        if not network:
            continue
        addKdramaEvent(service, title, network, cast, wiki, date, recurrence)

def getDramaInfo(wiki):
    soup = makeSoup(wiki)
    daysList = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    daysDict = {'Saturday':'SA', 'Sunday':'SU', 'Monday':'MO', 'Tuesday':'TU',
                'Wednesday':'WE', 'Thursday':'TH', 'Friday':'FR'}
    dramaInfo = soup.find("div", "mw-parser-output").findAll("ul")[1].contents
    episodes, network, days, recurrence = '', '', '', ''
    for elem in dramaInfo[::2]:
        if elem.b.text.lower() == 'episodes:':
            episodes = elem.text[10:]
        elif elem.b.text.lower() == 'broadcast network:':
            network = elem.text
        elif elem.b.text.lower() == 'air time:':
            strings = elem.text[10:]
            regex = re.compile('[^a-zA-Z ]')
            strings = regex.sub('', strings).split()
            if 'to' in strings:
                start = daysList.index(strings[0])
                end = daysList.index(strings[2])
                while start != end:
                    days += daysDict[daysList[start]] + ','
                    start = (start + 1) % 7
                days += daysDict[daysList[end]]
            else:
                for item in strings:
                    if item in daysDict:
                        days += daysDict[item] + ','
                days = days[:-1]
            if days:
                recurrence = 'RRULE:FREQ=WEEKLY;COUNT=' + episodes + ';WKST=SU;BYDAY=' + days
    if not episodes or len(episodes) > 3:
        network = ''
    return network, recurrence

def addKdramaEvent(service, title, network, cast, wiki, date, recurrence):
    formattedDate = datetime.strptime(date, '%Y-%b-%d\n')
    regex = re.compile('[^a-v0-9]')
    id = regex.sub('', wiki)
    event = {
        'summary': title,
        'transparency': 'transparent',
        'id': id,
        'description': network + '\n' + 'Cast: ' + cast + wiki,
        'start': {
            'date': formattedDate.strftime('%Y-%m-%d'),
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'date': formattedDate.strftime('%Y-%m-%d'),
            'timeZone': 'America/Los_Angeles',
        },
    }
    if recurrence:
        event['recurrence'] = [recurrence]
    try:
        service.events().insert(calendarId = kdramaCalId, body = event).execute()
    except Exception:
        service.events().update(calendarId = kdramaCalId, eventId = id, body = event).execute()


creds = None
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'client_secret.json', SCOPES)
        creds = flow.run_local_server()
    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('calendar', 'v3', credentials=creds)
updateKdrama(service)
