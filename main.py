from datetime import datetime
import json
import os
import oyez_api_wrapper
import sys
from typing import Dict, List
from urllib.parse import urlparse


DELETE_TEMP = False
NONE_STRING = 'NO_VALUE'


class CaseCrawler:
    is_valid: bool

    url: str
    term: str
    docket: str

    case_json_path: str
    case_data_path: str

    case_json: Dict[str, str]
    case_data: List[str]


    def __init__(self, url: str) -> None:
        self.is_valid = False

        self.url = url
        self.term = NONE_STRING
        self.docket = NONE_STRING

        self.case_json_path = ''
        self.case_data_path = ''

        self.case_json = {}
        self.case_data = []

        self.parse_url()


    def parse_url(self) -> None:
        url_parsed = urlparse(self.url)

        url_items = [part for part in url_parsed.path.split('/') if part]

        is_oyez_location = url_parsed.netloc == 'www.oyez.org'
        is_case_entry = len(url_items) == 3 and url_items[0] == 'cases'

        self.is_valid = is_oyez_location and is_case_entry

        if self.is_valid:
            self.term = url_items[1]
            self.docket = url_items[2]

            self.case_json_path = f'oyez_{self.term}_{self.docket}.json'
            self.case_data_path = f'case_{self.term}_{self.docket}.txt'


    def process_case(self) -> None:
        if self.is_valid is False:
            return
        
        case_obj = oyez_api_wrapper.court_case(self.term, self.docket)
        case_obj.download_court_json('')

        os.rename(self.case_json_path, f'data/{self.case_json_path}')

        with open(f'data/{self.case_json_path}', 'r') as json_file:
            self.case_json = json.load(json_file)

        self.get_case_data()
        self.write_case_data()


    def get_case_data(self) -> None:
        self.get_case_info()
        self.get_case_opinions()
        self.get_case_body()
        self.get_case_meta()


    def write_case_data(self) -> None:
        with open(f'data/{self.case_data_path}', 'w') as case_data_file:
            case_data_file.write('\n'.join(self.case_data))
        
        if DELETE_TEMP and os.path.exists(f'data/{self.case_json_path}'):
            os.remove(f'data/{self.case_json_path}')


    def get_case_info(self) -> None:
        self.case_data.append('TITLE')
        self.case_data.append(f'{self.case_json['name']}\n')

        self.case_data.append('JUSTIA')
        self.case_data.append(f'{self.case_json['justia_url']}\n')


    def get_case_opinions(self) -> None:
        syllabus = None
        majority = None
        opinions = []
        separate_opinions = []

        if self.case_json['written_opinion']:
            opinions = self.case_json['written_opinion'] 

        for opinion in opinions:
            opinion_type = opinion['type']['value']

            if opinion_type == 'syllabus':
                syllabus = opinion
            elif opinion_type == 'majority':
                majority = opinion
            elif opinion_type != 'case':
                separate_opinions.append(opinion)

        self.case_data.append('SYLLABUS VALUE')
        self.case_data.append(f'{syllabus['type']['label']}\n' if syllabus else f'{NONE_STRING}\n')

        self.case_data.append('SYLLABUS LINK')
        self.case_data.append(f'{syllabus['justia_opinion_url']}/#tab-opinion-{syllabus['justia_opinion_id']}\n' if syllabus else f'{NONE_STRING}\n')

        self.case_data.append('OYEZ URL')
        self.case_data.append(f'{self.case_json['href'].replace('api.', 'www.')}\n')

        self.case_data.append('DELIVERED BY')
        self.case_data.append(f'{majority['judge_full_name']}\n' if majority else f'{NONE_STRING}\n')

        self.case_data.append('OPINION OF THE COURT')
        self.case_data.append(f'{majority['justia_opinion_url']}/#tab-opinion-{majority['justia_opinion_id']}\n' if majority else f'{NONE_STRING}\n')

        for separate_opinion in separate_opinions:
            self.case_data.append('JUSTICE')
            self.case_data.append(f'{separate_opinion['judge_full_name']}\n')

            self.case_data.append('TYPE OF OPINION')
            self.case_data.append(f'{separate_opinion['type']['label']}\n')

            self.case_data.append('LINK')
            self.case_data.append(f'{separate_opinion['justia_opinion_url']}/#tab-opinion-{separate_opinion['justia_opinion_id']}\n')


    def get_case_body(self) -> None:
        self.case_data.append('CONTENT')
        self.case_data.append(f'{self.case_json['facts_of_the_case']}\n')

        self.case_data.append('QUESTION')
        self.case_data.append(f'{self.case_json['question']}\n')

        self.case_data.append('CONCLUSION')
        self.case_data.append(f'{self.case_json['conclusion']}\n')


    def get_case_meta(self) -> None:
        self.case_data.append('PETITIONER')
        self.case_data.append(f'{self.case_json['first_party']}\n')

        self.case_data.append('RESPONDENT')
        self.case_data.append(f'{self.case_json['second_party']}\n')

        self.case_data.append('DOCKET NUMBER')
        self.case_data.append(f'{self.case_json['docket_number']}\n')

        self.case_data.append('DECIDED BY')
        self.case_data.append(f'{self.case_json['decided_by']['name']}\n' if self.case_json['decided_by'] else f'{NONE_STRING}\n')

        self.case_data.append('LOWER COURT')
        self.case_data.append(f'{self.case_json['lower_court']['name']}\n' if self.case_json['lower_court'] else f'{NONE_STRING}\n')

        if self.case_json['citation']['volume']:
            volume = self.case_json['citation']['volume']
            page = f' US {self.case_json['citation']['page']}' if self.case_json['citation']['page'] else ' US __'
            year = f' ({self.case_json['citation']['year']})' if self.case_json['citation']['year'] else ''

            self.case_data.append('CITATION TEXT')
            self.case_data.append(f'{volume}{page}{year}\n')

            self.case_data.append('CITATION URL')
            self.case_data.append(f'https://supreme.justia.com/cases/federal/us/{volume}/{self.case_json['docket_number']}/\n')
        else:
            self.case_data.append('CITATION TEXT')
            self.case_data.append(f'{NONE_STRING}\n')

            self.case_data.append('CITATION URL')
            self.case_data.append(f'{NONE_STRING}\n')

        self.format_timepoint('Granted')
        self.format_timepoint('Argued')
        self.format_timepoint('Decided')

        if self.case_json['advocates']:
            for advocate in self.case_json['advocates']:
                if advocate and advocate['advocate']:
                    self.case_data.append('ADVOCATE NAME')
                    self.case_data.append(f'{advocate['advocate']['name']}\n')

                    self.case_data.append('ADVOCATE LINK')
                    self.case_data.append(f'https://www.oyez.org/advocates/{advocate['advocate']['identifier']}\n')

                    self.case_data.append('ADVOCATE DESCRIPTION')
                    self.case_data.append(f'{advocate['advocate_description']}\n')


    def format_timepoint(self, event: str) -> None:
        result = next(
            (timepoint for timepoint in self.case_json['timeline'] if timepoint['event'] == event), 
            None
        )

        if result:
            date = datetime.fromtimestamp(result['dates'][0]).strftime('%d-%m-%Y')

            self.case_data.append(event.upper())
            self.case_data.append(f'{date}\n')
        else:
            self.case_data.append(event.upper())
            self.case_data.append(f'{NONE_STRING}\n')


def main() -> None:
    url = sys.argv[1]

    case_crawler = CaseCrawler(url)

    case_crawler.process_case()


if __name__ == '__main__':
    main()
