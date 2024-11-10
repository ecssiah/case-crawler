from datetime import datetime
import json
import sys
from typing import Dict, List
import os
import oyez_api_wrapper
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
        if not self.is_valid:
            return
        
        case_obj = oyez_api_wrapper.court_case(self.term, self.docket)
        case_obj.download_court_json('')

        os.rename(self.case_json_path, f'data/{self.case_json_path}')

        with open(f'data/{self.case_json_path}', 'r') as json_file:
            self.case_json = json.load(json_file)

        self.get_case_data()
        self.write_case_data()

    
    def get_case_data(self) -> None:
        self.format_case_info()
        self.format_case_opinions()
        self.format_case_body()
        self.format_case_meta()


    def write_case_data(self) -> None:
        with open(f'data/{self.case_data_path}', 'w') as case_data_file:
            case_data_file.write('\n'.join(self.case_data))
        
        if DELETE_TEMP and os.path.exists(f'data/{self.case_json_path}'):
            os.remove(f'data/{self.case_json_path}')


    def format_case_info(self) -> None:
        self.case_data.append('TITLE')
        self.case_data.append(f'{self.case_json['name']}')
        self.case_data.append('')

        self.case_data.append('JUSTIA')
        self.case_data.append(f'{self.case_json['justia_url']}')
        self.case_data.append('')


    def format_case_opinions(self) -> None:
        syllabus = None
        majority = None
        separate_opinions = []

        opinions = self.case_json['written_opinion'] if self.case_json['written_opinion'] else []
        
        for opinion in opinions:
            opinion_type = opinion['type']['value']

            if opinion_type == 'syllabus':
                syllabus = opinion
            elif opinion_type == 'majority':
                majority = opinion
            elif opinion_type != 'case':
                separate_opinions.append(opinion)
        
        self.case_data.append('SYLLABUS VALUE')
        self.case_data.append(f'{syllabus['type']['label']}' if syllabus else NONE_STRING)
        self.case_data.append('SYLLABUS LINK')
        self.case_data.append(f'{syllabus['justia_opinion_url']}/#tab-opinion-{syllabus['justia_opinion_id']}' if syllabus else NONE_STRING)
        self.case_data.append('')

        self.case_data.append('OYEZ URL')
        self.case_data.append(self.case_json['href'].replace('api.', 'www.'))
        self.case_data.append('')

        self.case_data.append('DELIVERED BY')
        self.case_data.append(f'{majority['judge_full_name']}' if majority else NONE_STRING)
        self.case_data.append('OPINION OF THE COURT')
        self.case_data.append(f'{majority['justia_opinion_url']}/#tab-opinion-{majority['justia_opinion_id']}' if majority else NONE_STRING)
        self.case_data.append('')

        for separate_opinion in separate_opinions:
            self.case_data.append('JUSTICE')
            self.case_data.append(f'{separate_opinion['judge_full_name']}')
            self.case_data.append('TYPE OF OPINION')
            self.case_data.append(f'{separate_opinion['type']['label']}')
            self.case_data.append('LINK')
            self.case_data.append(f'{separate_opinion['justia_opinion_url']}/#tab-opinion-{separate_opinion['justia_opinion_id']}')
            self.case_data.append('')


    def format_case_body(self) -> None:
        self.case_data.append('CONTENT')
        self.case_data.append(f'{self.case_json['facts_of_the_case']}')
        self.case_data.append('')

        self.case_data.append('QUESTION')
        self.case_data.append(f'{self.case_json['question']}')
        self.case_data.append('')

        self.case_data.append('CONCLUSION')
        self.case_data.append(f'{self.case_json['conclusion']}')
        self.case_data.append('')


    def format_case_meta(self) -> None:
        self.case_data.append('PETITIONER')
        self.case_data.append(f'{self.case_json['first_party']}')
        self.case_data.append('')

        self.case_data.append('RESPONDENT')
        self.case_data.append(f'{self.case_json['second_party']}')
        self.case_data.append('')

        self.case_data.append('DOCKET NUMBER')
        self.case_data.append(f'{self.case_json['docket_number']}')
        self.case_data.append('')

        self.case_data.append('DECIDED BY')
        self.case_data.append(f'{self.case_json['decided_by']['name']}' if self.case_json['decided_by'] else NONE_STRING)
        self.case_data.append('')

        self.case_data.append('LOWER COURT')
        self.case_data.append(f'{self.case_json['lower_court']['name']}' if self.case_json['lower_court'] else NONE_STRING)
        self.case_data.append('')

        if self.case_json['citation']['volume']:
            volume = self.case_json['citation']['volume']
            page = f' US {self.case_json['citation']['page']}' if self.case_json['citation']['page'] else ' US __'
            year = f' ({self.case_json['citation']['year']})' if self.case_json['citation']['year'] else ''

            self.case_data.append('CITATION TEXT')
            self.case_data.append(f'{volume}{page}{year}')
            self.case_data.append('CITATION URL')
            self.case_data.append(f'https://supreme.justia.com/cases/federal/us/{volume}/{self.case_json['docket_number']}/')
            self.case_data.append('')
        else:
            self.case_data.append('CITATION TEXT')
            self.case_data.append(NONE_STRING)
            self.case_data.append('CITATION URL')
            self.case_data.append(NONE_STRING)
            self.case_data.append('')

        self.format_timepoint('Granted')
        self.format_timepoint('Argued')
        self.format_timepoint('Decided')

        if self.case_json['advocates']:
            for advocate in self.case_json['advocates']:
                if advocate and advocate['advocate']:
                    self.case_data.append('ADVOCATE NAME')
                    self.case_data.append(f'{advocate['advocate']['name']}')
                    self.case_data.append('ADVOCATE LINK')
                    self.case_data.append(f'https://www.oyez.org/advocates/{advocate['advocate']['identifier']}')
                    self.case_data.append('ADVOCATE DESCRIPTION')
                    self.case_data.append(f'{advocate['advocate_description']}')
                    self.case_data.append('')


    def format_timepoint(self, event: str) -> None:
        result = next(
            (timepoint for timepoint in self.case_json['timeline'] if timepoint['event'] == event), 
            None
        )

        if result:
            date = datetime.fromtimestamp(result['dates'][0]).strftime('%d-%m-%Y')

            self.case_data.append(event.upper())
            self.case_data.append(f'{date}')
            self.case_data.append('')
        else:
            self.case_data.append(event.upper())
            self.case_data.append(NONE_STRING)
            self.case_data.append('')


def main() -> None:
    url = sys.argv[1]

    case_crawler = CaseCrawler(url)

    case_crawler.process_case()


if __name__ == '__main__':
    main()
