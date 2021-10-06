import json

import requests
import os
import re
import jwt
from jinja2 import Template
import datetime
import getpass
import urllib.parse
import sys
from tqdm.auto import tqdm


class HL:
    def __init__(self):
        self.token = ''
        self.csrf = '3nbeS3PJQjCBdpFG3nbeS3PJQjCBdpFG'
        self.baseUrl = 'https://ost.hacking-lab.com/api'
        self.given_name = ''
        self.family_name = ''
        self.preferred_username = ''
        self.author = ''
        self.cred = {}
        self.token_time = datetime.datetime.now()

    def connect(self, cred):
        self.cred = cred
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'scope': 'openid',
            'client_id': 'ccs',
            'grant_type': 'password',
            'username': cred['username'],
            'password': cred['password']
        }
        response = requests.post('https://auth.ost-dc.hacking-lab.com/auth/realms/ost/protocol/openid-connect/token',
                                 data=data,
                                 headers=headers).json()
        self.token = response['access_token']
        self.token_time = datetime.datetime.now() + datetime.timedelta(0, )
        payload = jwt.decode(self.token, options={"verify_signature": False})
        self.given_name = payload['given_name']
        self.family_name = payload['family_name']
        self.preferred_username = payload['preferred_username']
        self.author = self.given_name + ' ' + self.family_name + ' (' + self.preferred_username + ')'

    def check_token(self):
        try:
            jwt.decode(self.token, options={"verify_signature": False, "verify_exp": True})
        except jwt.ExpiredSignatureError:
            # Signature has expired
            self.connect(self.cred)

    def get(self, url):
        self.check_token()
        call_url = urllib.parse.urljoin(self.baseUrl, url)
        cookies = {'Authentication': self.token, 'CSRF-TOKEN': self.csrf}
        headers = {'x-csrf-token': self.csrf}
        response = requests.get(call_url, cookies=cookies)
        response.raise_for_status()
        return response

    def put(self, url, data):
        self.check_token()
        call_url = urllib.parse.urljoin(self.baseUrl, url)
        cookies = {'Authentication': self.token, 'CSRF-TOKEN': self.csrf}
        headers = {'x-csrf-token': self.csrf, 'Content-type': 'application/json'}
        res = requests.put(call_url, data=data, cookies=cookies, headers=headers)
        res.raise_for_status()
        return res

    def download_file(self, url, dest_filepath):
        self.check_token()
        if os.path.exists(dest_filepath):
            return
        call_url = urllib.parse.urljoin(self.baseUrl, url)
        cookies = {'Authentication': self.token, 'CSRF-TOKEN': self.csrf}
        # NOTE the stream=True parameter below
        with requests.get(call_url, stream=True, cookies=cookies) as r:
            r.raise_for_status()
            with open(dest_filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    # if chunk:
                    f.write(chunk)

    def get_all_events(self):
        return self.get("/api/user/events").json()

    def get_own_events(self):
        return self.get("/api/user/events?type=CURRICULUM,STANDALONE_EVENT").json()

    def get_event(self, event_id):
        return self.get('/api/user/events/' + str(event_id)).json()

    def get_curriculumevents(self, eventid):
        return self.get('/api/user/events/' + str(eventid) + '/curriculumevents/').json()

    def get_units(self, eventid):
        return self.get('/api/user/events/' + str(eventid) + '/units/').json()

    def get_challenge(self, unit):
        challenge_id = ''
        if type(unit['id']) == int or float:
            challenge_id = str(unit['id'])
        if unit['type'] == 'THEORY':
            _challenge = self.get('/api/user/theories/' + challenge_id).json()
        else:
            _challenge = self.get('/api/user/challenges/' + challenge_id).json()
        for i, section in enumerate(_challenge['sections']):
            try:
                section['steps'] = self.get_steps(_challenge['id'], section['id'])
            except requests.HTTPError as e:
                section['steps'] = []
        return _challenge

    def get_challenge_comment(self, unit):
        challengeid = ''
        # api/user/challenges/1786/comments/
        if type(unit['id']) == int or float:
            challengeid = str(unit['id'])
        comments = self.get('/api/user/challenges/' + challengeid + '/comments/').json()
        return comments

    def get_steps(self, challenge_id, section_id):
        return self.get('/api/user/challenges/' + str(challenge_id) + '/sections/' + section_id
                        + '/steps/').json()

    def start_container(self, challenge_id, resource_id):
        return self.put('/api/user/challenges/' + str(challenge_id) + '/resources/' + resource_id,
                        '{"requestedOperation":"START"}').json()

    # ---------------------------------------------
    def download_resources(self, base_path, challenge):
        if 'resources' in challenge.keys():
            for resource in challenge['resources']:
                if resource['type'] == 'FILE':
                    res = self.start_container(challenge['id'], resource['id'])
                    download_url = res['hyperlink'] + '/' + res['id'] + '/' + res['name']
                    filename = os.path.join(base_path, res['name'])
                    self.download_file(download_url, filename)

    def download_medias(self, challenge_folder, challenge):
        for section in challenge['sections']:
            self.download_medias_from_content(challenge_folder, section['content'])
            self.download_medias_from_steps(challenge_folder, section['steps'])

    def download_medias_from_steps(self, folder, steps):
        for step in steps:
            self.download_medias_from_content(folder, step['content'])

    def download_medias_from_content(self, challenge_folder, content):
        for media in media_links(content):
            url = media[1]
            filename = url_to_filename(url)
            if is_download_media_valid(filename):
                path = os.path.join(challenge_folder, filename)
                self.download_file(url, path)

    def download_comment_attachments(self, path_comment_folder, comments):
        for comment in comments:
            if 'attachment' in comment.keys():
                filename = os.path.join(path_comment_folder,
                                        str(comment['attachment']['id']) + "_" + comment['attachment']['name'])
                self.download_file("/api/attachments/" + str(comment['attachment']['id']), filename)


def media_links(content):
    return re.findall(r'\[(.*?)\]\((.*?)\)', content)


def url_to_filename(url):
    return url.split('/')[-1]


def is_download_media_valid(filename):
    return re.match(r"(.*?)\.(jpg|png|gif|doc|pdf|mp4|txt|apk)$", filename)


def render_template(data, fullpath, template):
    #    if os.path.exists(fullpath):
    #        return
    with open(template) as f:
        content = f.read()
    template = Template(content)
    output_content = template.render(data)
    f = open(fullpath, "w", encoding="utf-8")
    f.write(output_content)
    f.close()


def write_challange_content(path, event, curriculumevent, challange):
    render_template({
        'event': event,
        'curriculum': curriculumevent,
        'challange': challange
    }, path, 'README.template.md')


def write_writeup_content(path, event, curriculumevent, challange, author):
    render_template({
        'event': event,
        'curriculum': curriculumevent,
        'challange': challange,
        'author': author
    }, path, 'WRITEUP.template.md')


def write_comment_content(path, comments):
    render_template({
        'comments': comments,
    }, path, 'COMMENTS.template.md')


def replace_medialink_in_content_with_local_filename(content):
    for media_link in media_links(content):
        filename = url_to_filename(media_link[1])
        content.replace(media_link[1], filename)


def makedir(path):
    os.makedirs(path, exist_ok=True)


def remove_links(challenge):
    for section in challenge['sections']:
        section['content'] = remove_links_from_content(section['content'])
        section['steps'] = remove_links_from_steps(section['steps'])
    return challenge


def remove_links_from_steps(steps):
    for step in steps:
        step['content'] = remove_links_from_content(step['content'])
    return steps


def remove_links_from_content(content):
    new_content = content
    for media in media_links(content):
        url = media[1]
        filename = url_to_filename(url)
        new_content = new_content.replace(url, "medias/" + filename)
    return new_content


def make_valid_filename(s):
    if not s:
        return ''
    badchars = '\\/:*?\"<>|'
    for c in badchars:
        s = s.replace(c, '')
    return s


def create_path(base_folder, event, curriculumevent, unit, child_folder=''):
    return os.path.join(base_folder, remove_umlaut(event['name']).strip(),
                        str(curriculumevent['sortOrder'] + 1).zfill(2) + ' - ' + make_valid_filename(
                            remove_umlaut(curriculumevent['name'])).strip(),
                        str(unit['sortOrder'] + 1).zfill(2) + ' - ' + make_valid_filename(
                            remove_umlaut(unit['title'])).strip(), child_folder.strip())


def remove_umlaut(string):
    """
    Removes umlauts from strings and replaces them with the letter+e convention
    :param string: string to remove umlauts from
    :return: unumlauted string
    """
    u = 'ü'.encode()
    U = 'Ü'.encode()
    a = 'ä'.encode()
    A = 'Ä'.encode()
    o = 'ö'.encode()
    O = 'Ö'.encode()
    ss = 'ß'.encode()

    string = string.encode()
    string = string.replace(u, b'ue')
    string = string.replace(U, b'Ue')
    string = string.replace(a, b'ae')
    string = string.replace(A, b'Ae')
    string = string.replace(o, b'oe')
    string = string.replace(O, b'Oe')
    string = string.replace(ss, b'ss')

    string = string.decode('utf-8')
    return string


def get_credentials():
    cred_file = ".hl-cred.json"
    if os.path.exists(cred_file):
        f = open(cred_file, )
        data = json.load(f)
        return data
    cred_file = "~/.hl-cred.json"
    if os.path.exists(cred_file):
        f = open(cred_file, )
        data = json.load(f)
        return data

    if sys.stdin.isatty():
        print("Username: ", end='')
        username = input()
        password = getpass.getpass(prompt='Password: ', stream=None)
    else:
        username = sys.stdin.readline().rstrip()
        password = sys.stdin.readline().rstrip()
    return {
        'username': username,
        'password': password
    }


if __name__ == '__main__':
    hl = HL()
    credentials = get_credentials()
    hl.connect(credentials)
    base_folder = '.'

    events = hl.get_own_events()
    bar_event = tqdm(events, desc="Events")
    for event in bar_event:
        bar_event.set_description(event['name'])
        try:
            bar_curriculumevent = tqdm(hl.get_curriculumevents(event['id']), desc="Curriculum", leave=False)
        except requests.HTTPError as e:
            continue
        for curriculumevent in bar_curriculumevent:
            try:
                units = hl.get_units(curriculumevent['id'])
            except requests.HTTPError as e:
                continue
            if not isinstance(units, list):
                continue
            bar_curriculumevent.set_description(curriculumevent['name'])
            bar_unit = tqdm(units, desc="Challanges ", leave=False)
            for unit in bar_unit:
                bar_unit.set_description(unit['title'])
                # Setup
                valid_path_event_name = make_valid_filename(event['name'])
                valid_path_curriculumevent_name = make_valid_filename(curriculumevent['name'])
                challenge = hl.get_challenge(unit)
                unit_folder = create_path(base_folder, event, curriculumevent, unit, '')
                makedir(unit_folder)

                # Download resources from challange task
                path_resource_folder = create_path(base_folder, event, curriculumevent, unit, 'resources')
                makedir(path_resource_folder)
                hl.download_resources(path_resource_folder, challenge)

                # Download attachments from comments
                path_comment_folder = create_path(base_folder, event, curriculumevent, unit, 'comments')
                makedir(path_comment_folder)
                hl.download_comment_attachments(path_comment_folder, hl.get_challenge_comment(unit))

                # Download media from Challange description
                path_media_folder = create_path(base_folder, event, curriculumevent, unit, 'medias')
                makedir(path_media_folder)
                hl.download_medias(path_media_folder, challenge)

                challenge = remove_links(challenge)

                # Create README.md
                challenge_file = create_path(base_folder, event, curriculumevent, unit, 'README.md')
                write_challange_content(challenge_file, event, curriculumevent, challenge)
                # Create COMMENT.md
                comment_file = create_path(base_folder, event, curriculumevent, unit, 'COMMENT.md')
                # Crete WRITEUP.md
                write_comment_content(comment_file, hl.get_challenge_comment(unit))
                writeup_file = create_path(base_folder, event, curriculumevent, unit, 'WRITEUP.md')
                write_writeup_content(writeup_file, event, curriculumevent, challenge, hl.author)
