"""
Provides methods to establish a connection to the GPRO website as well as
scrape and parse its contents.
"""
from dataclasses import dataclass, field, asdict
import datetime
import logging
import re
from getpass import getpass

import requests
from bs4 import BeautifulSoup


@dataclass
class DriverDataClass:
    name: str
    oa: int
    concentration: int
    talent: int
    aggressiveness: int
    experience: int
    technical_insight: int
    stamina: int
    charisma: int
    motivation: int
    reputation: int
    weight: int


@dataclass
class SetupDataClass:
    tyre: str
    front_wing: int
    rear_wing: int
    engine: int
    brakes: int
    gearbox: int
    suspension: int


@dataclass
class PracticeLapDataClass:
    setup: SetupDataClass
    lap_time: datetime.timedelta
    net_time: datetime.timedelta
    driver_mistake: datetime.timedelta
    comments: str


@dataclass
class RaceRiskData:
    overtake: int = None
    defend: int = None
    clear: int = None
    malfunct: int = None


@dataclass
class EnergyDataClass:
    q1_pre: int = None
    q1_post: int = None
    q2_pre: int = None
    q2_post: int = None
    race_pre: int = None
    race_post: int = None


@dataclass
class CcpDataClass:
    power: int = None
    handling: int = None
    acceleration: int = None


@dataclass
class TyreSupplierDataClass:
    name: str
    peak_temperature: int
    dry: int
    wet: int
    durability: int
    warmup: int


@dataclass
class QualifyingData:
    setup: SetupDataClass = None
    fuel: int = None
    risk: str = None
    temperature: int = None
    humidity: int = None
    weather: str = None
    lap_time: datetime.timedelta = None


@dataclass
class WeatherForecastData:
    temperature_min: int = None
    temperature_max: int = None
    humidity_min: int = None
    humidity_max: int = None
    rain_probability: int = None


@dataclass
class PitStopData:
    lap: int = None
    reason: str = None
    tyre_condition: int = None
    fuel_left_percent: int = None
    fuel_refilled: int = None
    time: datetime.timedelta = None


@dataclass
class TechProblemData:
    lap: int = None
    details: str = None


@dataclass
class OvertakingData:
    initiated_blocked: int = None
    initiated_successful: int = None
    on_you_blocked: int = None
    on_you_successful: int = None


@dataclass
class FinancesData:
    total_income: int = None
    race_position: int = None
    qualifying_position: int = None
    sponsor: int = None
    driver_salary: int = None
    staff_salary: int = None
    facility_cost: int = None
    tyre_cost: int = None


@dataclass
class CarPartData:
    chassis: int = None
    engine: int = None
    front_wing: int = None
    rear_wing: int = None
    underbody: int = None
    sidepods: int = None
    cooling: int = None
    gearbox: int = None
    brakes: int = None
    suspension: int = None
    electronics: int = None


@dataclass
class LapData:
    lap: int = None
    boost: bool = None
    time: datetime.timedelta = None
    position: int = None
    tyres: str = None
    weather: str = None
    temperature: int = None
    humidity: int = None
    events: str = None


@dataclass
class RaceAnalysisData:
    track_name: str = None
    track_id: str = None
    season: int = None
    race: int = None
    group: str = None
    practice: list[PracticeLapDataClass] = field(default_factory=list)
    qualifying1: QualifyingData = QualifyingData()
    qualifying2: QualifyingData = QualifyingData()
    setup_race: SetupDataClass = None
    risk_race: RaceRiskData = None
    driver_stats: DriverDataClass = None
    driver_change: DriverDataClass = None
    energy: EnergyDataClass = None
    position_start: int = None
    position_finish: int = None
    ccp: CcpDataClass = None
    tyre_supplier: TyreSupplierDataClass = None
    weather: tuple[WeatherForecastData, WeatherForecastData, WeatherForecastData, WeatherForecastData] = field(
        default_factory=tuple)
    pitstops: list[PitStopData] = field(default_factory=list)
    problems: list[TechProblemData] = field(default_factory=list)
    tyre_condition_finish: int = None
    fuel_start: int = None
    fuel_left_finish: int = None
    overtaking: OvertakingData = None
    finances: FinancesData = None
    car_part_levels: CarPartData = None
    car_part_wear_start: CarPartData = None
    car_part_wear_finish: CarPartData = None
    lap_chart: list[LapData] = field(default_factory=list)
    notes: str = None


class GproScraper:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = self._session_login()
        logging.basicConfig()
        self.logger = logging.getLogger()

    def _session_login(self):
        return connection_init(self.username, self.password)

    def parse_race_analysis(self, season: int = None, race: int = None) -> RaceAnalysisData:
        """Download and parse the latest race analysis"""
        return parse_race_analysis(self.session, season, race)

    def parse_all_race_analysis(self) -> dict[tuple[int, int], RaceAnalysisData]:
        most_recent = self.parse_race_analysis()
        results = {(most_recent.season, most_recent.race): most_recent}
        for s in range(1, most_recent.season + 1):
            for r in range(1, 17):
                try:
                    data = self.parse_race_analysis(s, r)
                    results[(s, r)] = data
                    self.logger.log(logging.DEBUG, f"scraped Season {s}, Race {r} successfully.")
                except NotRacedError:
                    self.logger.log(logging.DEBUG, f"Season {s}, Race {r} was not raced. Skipping.")
                    continue
        self.logger.log(logging.DEBUG, f"successfully scraped {len(results)} races.")
        return results


def connection_init(username: str, password: str) -> requests.Session:
    """Initialize http session and log in"""
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
    except RuntimeError:
        print("Login failed. Response code: " + str(result.status_code))
    # print(result.status_code)
    # print(result.text)
    return session


class NotRacedError(Exception):
    pass


def parse_race_analysis(session, season: int = None, race: int = None):
    """
    Loads and parses the race analysis page
    :param session: a logged-in session
    :param season: the season of the race to be parsed
    :param race: the race number of the race to be parsed
    :return: RaceAnalysisData containing the parsed data
    """
    if season is None and race is None:
        html_page = session.get("https://gpro.net/gb/RaceAnalysis.asp")
    elif season is not None and race is not None:
        html_page = session.get(f"https://gpro.net/gb/RaceAnalysis.asp?SR={season},{race}")
    else:
        raise ValueError("season and race must either both be provided or neither.")
    parsed_page = BeautifulSoup(html_page.text, 'html.parser')

    # check for race participation and error if not participated

    if parsed_page.select_one(".center").text == f"You did not participate in Season {season}, Race {race}":
        raise NotRacedError(f"You did not participate in Season {season}, Race {race}")
        return

    data = RaceAnalysisData()
    # populate instance with basic info

    data.track_name = parsed_page.select_one(".block > a:nth-child(7)").text
    data.track_id = re.search(r"id=(\d*)", parsed_page.select_one(
        ".block > a:nth-child(7)").attrs.get("href")).group(1)
    # pull season, race number and group with regex
    regex = re.compile(r"Season (\d*) - Race (\d*) \((\w* - \d*)\)")
    regex.search(parsed_page.select_one(".block").text).group(1)
    data.season = int(regex.search(parsed_page.select_one(".block").text).group(1))
    data.race = int(regex.search(parsed_page.select_one(".block").text).group(2))
    data.group = regex.search(parsed_page.select_one(".block").text).group(3)

    (data.qualifying1.setup, data.qualifying2.setup, data.setup_race) = _parse_race_analysis_setups(parsed_page)

    return data


def _parse_race_analysis_setups(parsed_page: BeautifulSoup) -> tuple[SetupDataClass, SetupDataClass, SetupDataClass]:
    """
    parse the Setups used table on the Race analysis page
    :param parsed_page: BeautifulSoup object for the Race analysis page
    :return: tuple of SetupDataClass containing the setups and tyres used
    """
    setup_table = parsed_page.find("th", text="Setups used").parent.parent
    setups_dict = {
        "Q1": [ele.text.strip() for ele in setup_table.select_one("tr:nth-of-type(3)").find_all("td")],
        "Q2": [ele.text.strip() for ele in setup_table.select_one("tr:nth-of-type(4)").find_all("td")],
        "Race": [ele.text.strip() for ele in setup_table.select_one("tr:nth-of-type(5)").find_all("td")]
    }
    # clean up the lists and extract tyres
    setups_dict["Q1"].pop(0)
    setups_dict["Q1_tyres"] = setups_dict["Q1"].pop()
    setups_dict["Q2"].pop(0)
    setups_dict["Q2_tyres"] = setups_dict["Q2"].pop()
    setups_dict["Race"].pop(0)
    setups_dict["Race_tyres"] = setups_dict["Race"].pop()

    setup_q1 = SetupDataClass(setups_dict["Q1_tyres"], *setups_dict["Q1"])
    setup_q2 = SetupDataClass(setups_dict["Q2_tyres"], *setups_dict["Q2"])
    setup_race = SetupDataClass(setups_dict["Race_tyres"], *setups_dict["Race"])

    return setup_q1, setup_q2, setup_race


def terminal_login():
    """
    Requests username and password on the command line, creates a session
    and logs in.
    """
    username = input("GPRO-Username:")
    password = getpass("GPRO-Password:")
    scraper = GproScraper(username, password)
    return scraper


def manual_test_parse_all_race_analysis():
    scraper = terminal_login()
    results = scraper.parse_all_race_analysis()


def main():
    """Main method for manual testing purposes."""
    manual_test_parse_single_race_analysis(54, 14)


def manual_test_parse_single_race_analysis(season, race):
    scraper = terminal_login()
    try:
        parsed_race = scraper.parse_race_analysis(season, race)
    except NotRacedError as e:
        raise
    print(parsed_race)
    print(asdict(parsed_race))


if __name__ == "__main__":
    main()
