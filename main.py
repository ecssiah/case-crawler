from datetime import datetime
import json
import sys
from typing import Dict, List, Tuple
import os
import oyez_api_wrapper
from urllib.parse import urlparse


DELETE_TEMP = True
NONE_STRING = 'NO VALUE'


class CaseCrawler:
    url: str
    term: str
    docket: str

    is_valid: bool

    case_json_path: str
    case_data_path: str

    case_json: Dict[str, str]
    case_data: List[str]


    def __init__(self, url: str) -> None:
        self.url = url
        self.term = NONE_STRING
        self.docket = NONE_STRING

        self.is_valid = False

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

        if is_oyez_location and is_case_entry:
            self.is_valid = True
            
            self.term = url_items[1]
            self.docket = url_items[2]

            self.case_json_path = f'oyez_{self.term}_{self.docket}.json'
            self.case_data_path = f'cases/case_{self.term}_{self.docket}.txt'


    def process_case(self) -> None:
        case_obj = oyez_api_wrapper.court_case(self.term, self.docket)
        case_obj.download_court_json('')

        with open(self.case_json_path, 'r') as json_file:
            self.case_json = json.load(json_file)

        self.get_case_data()

        with open(self.case_data_path, 'w') as case_data_file:
            case_data_file.write('\n'.join(self.case_data))
        
        if DELETE_TEMP and os.path.exists(self.case_json_path):
            os.remove(self.case_json_path)

    
    def get_case_data(self) -> None:
        self.format_case_info()
        self.format_case_opinions()
        self.format_case_body()
        self.format_case_meta()


    def format_case_info(self) -> None:
        self.case_data.append('TITLE')
        self.case_data.append(f'{self.case_json['name']}')
        self.case_data.append('')

        self.case_data.append('JUSTIA')
        self.case_data.append(f'{self.case_json['justia_url']}')
        self.case_data.append('')


    def format_case_opinions(self) -> None:
        if self.case_json['written_opinion']:
            opinions = [
                opinion for opinion in self.case_json['written_opinion'] if opinion['type']['value'] != 'case'
            ]
            
            syllabus_result = next(
                (opinion for opinion in opinions if opinion['type']['value'] == 'syllabus'), 
                None
            )

            self.case_data.append('SYLLABUS VALUE')
            self.case_data.append(f'{syllabus_result['type']['label']}' if syllabus_result else NONE_STRING)
            self.case_data.append('SYLLABUS LINK')
            self.case_data.append(f'{syllabus_result['justia_opinion_url']}' if syllabus_result else NONE_STRING)
            self.case_data.append('')

            if syllabus_result:
                opinions.remove(syllabus_result)

            self.case_data.append('OYEZ URL')
            self.case_data.append(self.case_json['href'].replace('api.', 'www.'))
            self.case_data.append('')

            majority_result = next(
                (opinion for opinion in opinions if opinion['type']['value'] == 'majority'), 
                None
            )

            self.case_data.append('DELIVERED BY')
            self.case_data.append(f'{majority_result['judge_full_name']}' if majority_result else NONE_STRING)
            self.case_data.append('OPINION OF THE COURT')
            self.case_data.append(f'{syllabus_result['justia_opinion_url']}' if majority_result else NONE_STRING)
            self.case_data.append('')
        
            if majority_result: 
                opinions.remove(majority_result) 

            for opinion in opinions:
                self.case_data.append('JUSTICE')
                self.case_data.append(f'{opinion['judge_full_name']}')
                self.case_data.append('TYPE OF OPINION')
                self.case_data.append(f'{opinion['type']['label']}')
                self.case_data.append('LINK')
                self.case_data.append(f'{opinion['justia_opinion_url']}')
                self.case_data.append('')
        else:
            self.case_data.append('SYLLABUS VALUE')
            self.case_data.append(NONE_STRING)
            self.case_data.append('SYLLABUS LINK')
            self.case_data.append(NONE_STRING)
            self.case_data.append('')

            self.case_data.append('OYEZ URL')
            self.case_data.append(self.case_json['href'].replace('api.', 'www.'))
            self.case_data.append('')

            self.case_data.append('DELIVERED BY')
            self.case_data.append(NONE_STRING)
            self.case_data.append('OPINION OF THE COURT')
            self.case_data.append(NONE_STRING)
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

        granted_result = next(
            (timepoint for timepoint in self.case_json['timeline'] if timepoint['event'] == 'Granted'), 
            None
        )

        if granted_result:
            granted_date = datetime.fromtimestamp(granted_result['dates'][0]).strftime('%d-%m-%Y')

            self.case_data.append('GRANTED')
            self.case_data.append(f'{granted_date}')
            self.case_data.append('')
        else:
            self.case_data.append('GRANTED')
            self.case_data.append(NONE_STRING)
            self.case_data.append('')

        argued_result = next(
            (timepoint for timepoint in self.case_json['timeline'] if timepoint['event'] == 'Argued'), 
            None
        )

        if argued_result:
            argued_date = datetime.fromtimestamp(argued_result['dates'][0]).strftime('%d-%m-%Y')

            self.case_data.append('ARGUED')
            self.case_data.append(f'{argued_date}')
            self.case_data.append('')
        else:
            self.case_data.append('ARGUED')
            self.case_data.append(NONE_STRING)
            self.case_data.append('')

        decided_result = next(
            (timepoint for timepoint in self.case_json['timeline'] if timepoint['event'] == 'Decided'), 
            None
        )

        if decided_result:
            decided_date = datetime.fromtimestamp(decided_result['dates'][0]).strftime('%d-%m-%Y')

            self.case_data.append('DECIDED')
            self.case_data.append(f'{decided_date}')
            self.case_data.append('')
        else:
            self.case_data.append('DECIDED')
            self.case_data.append(NONE_STRING)
            self.case_data.append('')

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


def main() -> None:
    url = sys.argv[1]

    case_crawler = CaseCrawler(url)

    if case_crawler.is_valid:
        case_crawler.process_case()


if __name__ == '__main__':
    main()
