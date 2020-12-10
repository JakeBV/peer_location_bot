from asyncio import sleep

from datetime import datetime
from pytz import timezone
from time import mktime

from data.config import localization_texts
from misc import intra_requests
from misc import mongo
from services.utils import nickname_check


async def get_users_info(required_users: str or list, lang: str, avatar: bool = False) -> dict:
    if isinstance(required_users, list):
        nicknames = required_users
    else:
        get_nicknames = required_users.lower().split()
        nicknames = list(dict.fromkeys(get_nicknames))[:5]
    user_info_localization = localization_texts['user_info'][lang]
    texts = []
    intra_users = []
    for nickname in nicknames:
        nickname_valid = nickname_check(nickname)
        info = {}
        if nickname_valid:
            access_token = intra_requests.get_token()
            info = intra_requests.get_user(nickname, access_token)
        elif len(nickname) > 20:
            nickname = f'{nickname[:20]}...'
        text = eval(user_info_localization['not_found'])
        if info:
            await sleep(0.25)
            coalition = intra_requests.get_user_coalition(nickname, access_token)
            displayname = info['displayname']
            cursus_users = info['cursus_users']
            cursus_info = '\n'.join([f'<b>{c["cursus"]["name"]}:</b> {round(c["level"], 2)}' for c in cursus_users])
            primary_campus_id = [campus['campus_id'] for campus in info['campus_users'] if campus['is_primary']][0]
            campus = [campus['name'] for campus in info['campus'] if campus['id'] == primary_campus_id][0]
            image_url = ''
            if len(nicknames) < 2:
                image_url = info['image_url']
            location = info['location']
            await mongo.find_intra_user(nickname, location)
            if info['staff?']:
                location = user_info_localization['ask_adm']
            if location is None:
                await sleep(0.25)
                location = get_last_seen_time(nickname, access_token, user_info_localization)
            text = f'<b>{displayname}</b> aka {nickname}\n<b>{user_info_localization["coalition"]}:</b> ' \
                   f'{coalition}\n{cursus_info}\n<b>{user_info_localization["campus"]}:</b> {campus}\n<b>' \
                   f'{user_info_localization["location"]}:</b> {location}'
            if avatar and image_url:
                text += f'<a href="{image_url}">​</a>'
            intra_users.append(nickname)
        texts.append(text)
        await sleep(0.5)
    data = {'text': f'\n\n'.join(texts), 'intra_users': intra_users}
    return data


def get_last_seen_time(nickname: str, access_token: str, user_info_localization: dict) -> str:
    last_location_info = intra_requests.get_last_locations(nickname, access_token)
    if not last_location_info:
        text = user_info_localization['not_on_campus']
        return text[:text.index('.')].replace("f'", '')
    last_location_end = last_location_info[0]['end_at'].replace('Z', '+00:00')
    date = datetime.fromisoformat(last_location_end)
    now = datetime.now(timezone('UTC'))
    seconds = mktime(now.timetuple()) - mktime(date.timetuple())
    seconds_in_day = 60 * 60 * 24
    seconds_in_hour = 60 * 60
    seconds_in_minute = 60
    days = int(seconds // seconds_in_day)
    hours = int((seconds - (days * seconds_in_day)) // seconds_in_hour)
    minutes = int((seconds - (days * seconds_in_day) - (hours * seconds_in_hour)) // seconds_in_minute)
    days_gone = ''
    hours_gone = ''
    minutes_gone = ''
    if days:
        days_gone = f'{days}{user_info_localization["days"]} '
    if hours:
        hours_gone = f'{hours}{user_info_localization["hours"]} '
    if minutes:
        minutes_gone = f'{str(minutes).zfill(2)}{user_info_localization["minutes"]} '
    if not days and not hours and not minutes:
        minutes_gone = user_info_localization['just_now']
        text = eval(user_info_localization['not_on_campus'])
        return text[:text.rindex(' ')]
    return eval(user_info_localization['not_on_campus'])


def get_last_locations(nickname: str, lang: str) -> str:
    user_info_localization = localization_texts['user_info'][lang]
    last_location_localization = localization_texts['last_locations']
    local_time = last_location_localization[lang]['local_time']
    nickname_valid = nickname_check(nickname)
    if not nickname_valid:
        return eval(user_info_localization['not_found'])
    access_token = intra_requests.get_token()
    last_locations = intra_requests.get_last_locations(nickname, access_token)
    head = f'<b>{nickname.upper()}</b>'
    if isinstance(last_locations, list) and last_locations:
        campuses = intra_requests.get_campuses(access_token)
        texts = [f'<i>{local_time}</i>']
        for location in last_locations:
            campus = [(campus['name'], campus['time_zone']) for campus in campuses
                      if campus['id'] == location['campus_id']][0]
            begin_at = location['begin_at'].replace('Z', '+00:00')
            time_format = '%H:%M  %d.%m.%y'
            log_in_time = datetime.fromisoformat(begin_at).astimezone(timezone(campus[1])).strftime(time_format)
            log_out_time = last_location_localization[lang]['now']
            if location['end_at'] is not None:
                end_at = location['end_at'].replace('Z', '+00:00')
                log_out_time = datetime.fromisoformat(end_at).astimezone(timezone(campus[1])).strftime(time_format)
            log_time = f'{log_in_time} - {log_out_time}'
            if log_in_time[7:] == log_out_time[7:]:
                log_time = f'{log_in_time[:5]} - {log_out_time[:5]}  {log_in_time[7:]}'
            text = f'<b>{campus[0]} {location["host"]}</b>\n{log_time}'
            texts.append(text)
    elif isinstance(last_locations, list) and not last_locations:
        texts = [last_location_localization[lang]['not_logged']]
    else:
        return eval(user_info_localization['not_found'])
    return f'{head}\n' + f'\n'.join(texts)


def friends_list_normalization(message_text: str, friends: list, lang: str) -> str:
    friends_info = message_text.split('\n\n')
    friends_list = [s for s in friends_info[1:] if any(x in s for x in friends)]
    new_friends_info = []
    for info in friends_list:
        strings = info.splitlines()
        normal_strings = []
        for i, string in enumerate(strings):
            if i == 0:
                normal_strings.append(f'<b>{string[:string.index("aka")]}</b>{string[string.index("aka"):]}')
            else:
                normal_strings.append(f'<b>{string[:string.index(":") + 1]}</b>{string[string.index(":") + 1:]}')
        new_friends_info.append('\n'.join(normal_strings))
    if new_friends_info:
        new_friends_info.insert(0, f'<b>{friends_info[0]}</b>')
    else:
        new_friends_info = [localization_texts['friends'][lang]['no_friends']]
    return '\n\n'.join(new_friends_info)
