from datetime import datetime
import json
import sys
from typing import Dict, List
import os
import oyez_api_wrapper
from urllib.parse import urlparse


NONE_STRING = 'No Value'


def parse_url(url: str) -> Dict[str, str]:
    parsed_url = urlparse(url)

    url_parts = [part for part in parsed_url.path.split('/') if part]

    is_oyez_location = parsed_url.netloc == 'www.oyez.org'
    is_case_entry = len(url_parts) == 3 and url_parts[0] == 'cases'

    if is_oyez_location and is_case_entry:
        return {
            'term': url_parts[1],
            'docket': url_parts[2],
        }
    else:
        return {
            'term': '',
            'docket': '',
        }


def process_case(details: Dict[str, str], delete_temp: bool = True) -> None:
    case_obj = oyez_api_wrapper.court_case(details['term'], details['docket'])
    case_obj.download_court_json('')

    json_path = f'oyez_{details['term']}_{details['docket']}.json'

    with open(json_path, 'r') as json_file:
        case_json = json.load(json_file)

    case_data = format_case_json(case_json)
    case_data_path = f'cases/case_{details['term']}_{details['docket']}.txt'

    with open(case_data_path, 'w') as case_data_file:
        case_data_file.write('\n'.join(case_data))
    
    if delete_temp and os.path.exists(json_path):
        os.remove(json_path)


def format_case_json(case_json: Dict[str, str]) -> List[str]:
    case_data = []

    format_case_info(case_json, case_data)
    format_case_opinions(case_json, case_data)
    format_case_body(case_json, case_data)
    format_case_meta(case_json, case_data)

    return case_data


def format_case_info(case_json: Dict[str, str], case_data: List[str]) -> None:
    case_data.append('TITLE')
    case_data.append(f'{case_json['name']}')
    case_data.append('')

    case_data.append('JUSTIA')
    case_data.append(f'{case_json['justia_url']}')
    case_data.append('')


def format_case_opinions(case_json: Dict[str, str], case_data: List[str]) -> None:
    if case_json['written_opinion'] == None:
        case_data.append('SYLLABUS VALUE')
        case_data.append(NONE_STRING)
        case_data.append('SYLLABUS LINK')
        case_data.append(NONE_STRING)
        case_data.append('')

        case_data.append('OYEZ URL')
        case_data.append(case_json['href'].replace('api.', 'www.'))
        case_data.append('')

        case_data.append('DELIVERED BY')
        case_data.append(NONE_STRING)
        case_data.append('OPINION OF THE COURT')
        case_data.append(NONE_STRING)
        case_data.append('')

        return
    
    opinions = [opinion for opinion in case_json['written_opinion'] if opinion['type']['value'] != 'case']
    
    syllabus_result = next(
        (opinion for opinion in opinions if opinion['type']['value'] == 'syllabus'), 
        None
    )

    if syllabus_result:
        case_data.append('SYLLABUS VALUE')
        case_data.append(f'{syllabus_result['type']['label']}')
        case_data.append('SYLLABUS LINK')
        case_data.append(f'{syllabus_result['justia_opinion_url']}')
        case_data.append('')

        opinions.remove(syllabus_result)
    else:
        case_data.append('SYLLABUS VALUE')
        case_data.append(NONE_STRING)
        case_data.append('SYLLABUS LINK')
        case_data.append(NONE_STRING)
        case_data.append('')

    case_data.append('OYEZ URL')
    case_data.append(case_json['href'].replace('api.', 'www.'))
    case_data.append('')

    majority_result = next(
        (opinion for opinion in opinions if opinion['type']['value'] == 'majority'), 
        None
    )

    if majority_result:
        case_data.append('DELIVERED BY')
        case_data.append(f'{majority_result['judge_full_name']}')
        case_data.append('OPINION OF THE COURT')
        case_data.append(f'{syllabus_result['justia_opinion_url']}')
        case_data.append('')

        opinions.remove(majority_result)
    else:
        case_data.append('DELIVERED BY')
        case_data.append(NONE_STRING)
        case_data.append('OPINION OF THE COURT')
        case_data.append(NONE_STRING)
        case_data.append('')

    for opinion in opinions:
        case_data.append('JUSTICE')
        case_data.append(f'{opinion['judge_full_name']}')
        case_data.append('TYPE OF OPINION')
        case_data.append(f'{opinion['type']['label']}')
        case_data.append('LINK')
        case_data.append(f'{opinion['justia_opinion_url']}')
        case_data.append('')


def format_case_body(case_json: Dict[str, str], case_data: List[str]) -> None:
    case_data.append('CONTENT')
    case_data.append(f'{case_json['facts_of_the_case']}')
    case_data.append('')

    case_data.append('QUESTION')
    case_data.append(f'{case_json['question']}')
    case_data.append('')

    case_data.append('CONCLUSION')
    case_data.append(f'{case_json['conclusion']}')
    case_data.append('')


def format_case_meta(case_json: Dict[str, str], case_data: List[str]) -> None:
    case_data.append('PETITIONER')
    case_data.append(f'{case_json['first_party']}')
    case_data.append('')

    case_data.append('RESPONDENT')
    case_data.append(f'{case_json['second_party']}')
    case_data.append('')

    case_data.append('DOCKET NUMBER')
    case_data.append(f'{case_json['docket_number']}')
    case_data.append('')

    case_data.append('DECIDED BY')
    case_data.append(f'{case_json['decided_by']['name']}' if case_json['decided_by'] else NONE_STRING)
    case_data.append('')

    case_data.append('LOWER COURT')
    case_data.append(f'{case_json['lower_court']['name']}' if case_json['lower_court'] else NONE_STRING)
    case_data.append('')

    if case_json['citation']['volume']:
        volume = case_json['citation']['volume']
        page = case_json['citation']['page'] if case_json['citation']['page'] else '__'
        year = case_json['citation']['year'] if case_json['citation']['year'] else ''

        case_data.append('CITATION TEXT')
        case_data.append(f'{volume} US {page} ({year})' if year else '')
        case_data.append('CITATION URL')
        case_data.append(f'https://supreme.justia.com/cases/federal/us/{volume}/{case_json['docket_number']}/')
        case_data.append('')
    else:
        case_data.append('CITATION TEXT')
        case_data.append(NONE_STRING)
        case_data.append('CITATION URL')
        case_data.append(NONE_STRING)
        case_data.append('')

    granted_result = next(
        (timepoint for timepoint in case_json['timeline'] if timepoint['event'] == 'Granted'), 
        None
    )

    if granted_result:
        granted_date = datetime.fromtimestamp(granted_result['dates'][0]).strftime('%d-%m-%Y')

        case_data.append('GRANTED')
        case_data.append(f'{granted_date}')
        case_data.append('')
    else:
        case_data.append('GRANTED')
        case_data.append(NONE_STRING)
        case_data.append('')

    argued_result = next(
        (timepoint for timepoint in case_json['timeline'] if timepoint['event'] == 'Argued'), 
        None
    )

    if argued_result:
        argued_date = datetime.fromtimestamp(argued_result['dates'][0]).strftime('%d-%m-%Y')

        case_data.append('ARGUED')
        case_data.append(f'{argued_date}')
        case_data.append('')
    else:
        case_data.append('ARGUED')
        case_data.append(NONE_STRING)
        case_data.append('')

    decided_result = next(
        (timepoint for timepoint in case_json['timeline'] if timepoint['event'] == 'Decided'), 
        None
    )

    if decided_result:
        decided_date = datetime.fromtimestamp(decided_result['dates'][0]).strftime('%d-%m-%Y')

        case_data.append('DECIDED')
        case_data.append(f'{decided_date}')
        case_data.append('')
    else:
        case_data.append('DECIDED')
        case_data.append(NONE_STRING)
        case_data.append('')

    if case_json['advocates']:
        for advocate in case_json['advocates']:
            if advocate and advocate['advocate']:
                case_data.append('ADVOCATE NAME')
                case_data.append(f'{advocate['advocate']['name']}')
                case_data.append('ADVOCATE LINK')
                case_data.append(f'https://www.oyez.org/advocates/{advocate['advocate']['identifier']}')
                case_data.append('ADVOCATE DESCRIPTION')
                case_data.append(f'{advocate['advocate_description']}')
                case_data.append('')


def main() -> None:
    url = sys.argv[1]

    details = parse_url(url)

    if details['term'] and details['docket']:
        process_case(details)


if __name__ == '__main__':
    main()
