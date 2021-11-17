"""
Provides methods to establish a connection to the GPRO website as well as
scrape and parse its contents.
"""
import logging
import re
from getpass import getpass

import requests
from bs4 import BeautifulSoup


def connection_init(username, password):
    """Initialize an http session and log in"""
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
        result = session.post(login_url, data=login_data, headers=login_headers,
                              allow_redirects=False)
        assert result.status_code == 302
    except AssertionError:
        print("Login failed. Response code: " + str(result.status_code))
    # print(result.status_code)
    # print(result.text)
    return session


def parse_race_analysis(session):
    """
    Loads and parses the race analysis page
    :param session: a logged in session
    :return: json-object containing the parsed data
    """
    html_page = session.get("https://gpro.net/gb/RaceAnalysis.asp")
    parsed_page = BeautifulSoup(html_page.text, 'html.parser')

    # create regex to pull season, race number and league
    regex = re.compile(r"Season (\d*) - Race (\d*) \((\w* - \d*)\)")
    regex.search(parsed_page.select_one(".block").text).group(1)

    # populate dict with basic info
    data = {
        "track_name": parsed_page.select_one(".block > a:nth-of-type(2)").text,
        "track_id": re.search(r"id=(\d*)", parsed_page.select_one(
            ".block > a:nth-of-type(2)").attrs.get("href")).group(1),
        "season": regex.search(parsed_page.select_one(".block").text).group(1),
        "race": regex.search(parsed_page.select_one(".block").text).group(2),
        "league": regex.search(parsed_page.select_one(".block").text).group(3)
    }
    return data


def terminal_login():
    """
    Requests username and password on the command line, creates a session
    and logs in.
    """
    username = input("GPRO-Username:")
    password = getpass("GPRO-Password:")
    session = connection_init(username, password)
    return session


def main():
    """Main method for manual testing purposes."""
    session = terminal_login()
    parsed_race = parse_race_analysis(session)
    print(parsed_race)


if __name__ == "__main__":
    main()
