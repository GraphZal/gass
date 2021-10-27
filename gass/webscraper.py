import requests
import logging
from getpass import getpass

def connection_init(username, password):
    session = requests.Session()
    login_url = "https://gpro.net/gb/Login.asp"
    login_data = {'textLogin': username,
                  'textPassword': password,
                  'token': '',
                  'Logon': 'Login',
                  'LogonFake': 'Sign+in'}
    login_headers = {'User-Agent': 'Mozilla/5.0'}
    session.headers.update(login_headers)
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
    result = session.get(login_url)
    try:
        result = session.post(login_url, data=login_data, headers=login_headers, allow_redirects=False)
        assert(result.status_code == 302)
    except:
        print("Login failed. Response code: "+result.status_code)
    #print(result.status_code)
    #print(result.text)
    return session


def terminal_login():
    username = input("GPRO-Username:")
    password = getpass("GPRO-Password:")
    session = connection_init(username, password)
    return session

def main():

    s= terminal_login()
    r = s.get('https://gpro.net/gb/TrainingSession.asp')
    print(r.text)

if __name__ == "__main__":
    main()