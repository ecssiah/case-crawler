from datetime import datetime
import json
import sys
from typing import Any, Dict, List
import os
import oyez_api_wrapper
from urllib.parse import urlparse


NONE_VALUE = 'None'


def parse_url() -> Any:
    url = sys.argv[1]
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
        return None


def process_case_data(details: Dict[str, str]):
    case_obj = oyez_api_wrapper.court_case(details['term'], details['docket'])

    case_obj.download_court_json('')

    case_json_path = f'oyez_{details['term']}_{details['docket']}.json'

    with open(case_json_path, 'r') as case_json_file:
        case_data = json.load(case_json_file)
        case_info = format_case_data(case_data)

        case_json_file_path = f'cases/case_{details['term']}_{details['docket']}.txt'

        with open(case_json_file_path, 'w') as case_info_file:
            case_info_file.write('\n'.join(case_info))

        # if os.path.exists(case_json_path):
        #     os.remove(case_json_path)

        print(f'{case_data['name']} retrieved')


def format_basic_info(case_data: Dict, case_info: List[str]) -> None:
    case_info.append('JUSTIA')
    case_info.append(f'{case_data['justia_url']}')
    case_info.append('')

    case_info.append('TITLE')
    case_info.append(f'{case_data['name']}')
    case_info.append('')


def format_opinions(case_data: Dict, case_info: List[str]) -> None:
    if case_data['written_opinion'] == None:
        case_info.append('SYLLABUS VALUE')
        case_info.append(NONE_VALUE)
        case_info.append('SYLLABUS LINK')
        case_info.append(NONE_VALUE)

        case_info.append('')

        case_info.append('OYEZ URL')
        case_info.append(case_data['href'].replace('api.', 'www.'))
        case_info.append('')

        return
    
    opinions = [opinion for opinion in case_data['written_opinion'] if opinion['type']['value'] != 'case']
    
    syllabus_result = next(
        (opinion for opinion in opinions if opinion['type']['value'] == 'syllabus'), 
        None
    )

    if syllabus_result:
        case_info.append('SYLLABUS VALUE')
        case_info.append(f'{syllabus_result['type']['label']}')
        case_info.append('SYLLABUS LINK')
        case_info.append(f'{syllabus_result['justia_opinion_url']}')

        opinions.remove(syllabus_result)
    else:
        case_info.append('SYLLABUS VALUE')
        case_info.append(NONE_VALUE)
        case_info.append('SYLLABUS LINK')
        case_info.append(NONE_VALUE)

    case_info.append('')

    case_info.append('OYEZ URL')
    case_info.append(case_data['href'].replace('api.', 'www.'))
    case_info.append('')

    majority_result = next(
        (opinion for opinion in opinions if opinion['type']['value'] == 'majority'), 
        None
    )

    if majority_result:
        case_info.append('DELIVERED BY')
        case_info.append(f'{majority_result['judge_full_name']}')
        case_info.append('MAJORITY LINK')
        case_info.append(f'{syllabus_result['justia_opinion_url']}')

        opinions.remove(majority_result)
    else:
        case_info.append('DELIVERED BY')
        case_info.append(NONE_VALUE)
        case_info.append('MAJORITY LINK')
        case_info.append(NONE_VALUE)

    case_info.append('')

    for opinion in opinions:
        case_info.append('JUSTICE')
        case_info.append(f'{opinion['judge_full_name']}')
        case_info.append('TYPE OF OPINION')
        case_info.append(f'{opinion['type']['label']}')
        case_info.append('LINK')
        case_info.append(f'{opinion['justia_opinion_url']}')

        case_info.append('')


def format_body(case_data: Dict[str, Any], case_info: List[str]) -> None:
    case_info.append('CONTENT')
    case_info.append(f'{case_data['facts_of_the_case']}')
    case_info.append('')

    case_info.append('QUESTION')
    case_info.append(f'{case_data['question']}')
    case_info.append('')

    case_info.append('CONCLUSION')
    case_info.append(f'{case_data['conclusion']}')
    case_info.append('')


def format_case_meta(case_data: Dict[str, Any], case_info: List[str]) -> None:
    case_info.append('PETITIONER')
    case_info.append(f'{case_data['first_party']}')
    case_info.append('')

    case_info.append('RESPONDENT')
    case_info.append(f'{case_data['second_party']}')
    case_info.append('')

    case_info.append('DOCKET NUMBER')
    case_info.append(f'{case_data['docket_number']}')
    case_info.append('')

    case_info.append('DECIDED BY')
    if case_data['decided_by'] == None:
        case_info.append(NONE_VALUE)
    else:
        case_info.append(f'{case_data['decided_by']['name']}')
    case_info.append('')

    case_info.append('LOWER COURT')
    if case_data['lower_court'] == None:
        case_info.append(NONE_VALUE)
    else:
        case_info.append(f'{case_data['lower_court']['name']}')
    case_info.append('')

    if case_data['citation']['volume']:
        case_info.append('CITATION TEXT')

        volume = case_data['citation']['volume']
        page = case_data['citation']['page'] if case_data['citation']['page'] else '__'
        year = case_data['citation']['year'] if case_data['citation']['year'] else ''

        if year != '':
            case_info.append(f'{volume} US {page} ({year})')
        else:
            case_info.append(year)

        case_info.append('CITATION URL')
        case_info.append(f'https://supreme.justia.com/cases/federal/us/{volume}/{case_data['docket_number']}/')
    else:
        case_info.append('CITATION TEXT')
        case_info.append(NONE_VALUE)
        case_info.append('CITATION URL')
        case_info.append(NONE_VALUE)

    case_info.append('')

    granted_result = next(
        (point for point in case_data['timeline'] if point['event'] == 'Granted'), 
        None
    )

    if granted_result:
        case_info.append('GRANTED')
        granted_date = datetime.fromtimestamp(granted_result['dates'][0]).strftime('%m/%d/%Y')
        case_info.append(f'{granted_date}')
    else:
        case_info.append('GRANTED')
        case_info.append(NONE_VALUE)

    case_info.append('')

    argued_result = next(
        (point for point in case_data['timeline'] if point['event'] == 'Argued'), 
        None
    )

    if argued_result:
        case_info.append('ARGUED')
        argued_date = datetime.fromtimestamp(argued_result['dates'][0]).strftime('%m/%d/%Y')
        case_info.append(f'{argued_date}')
    else:
        case_info.append('ARGUED')
        case_info.append(NONE_VALUE)

    case_info.append('')

    decided_result = next(
        (point for point in case_data['timeline'] if point['event'] == 'Decided'), 
        None
    )

    if decided_result:
        case_info.append('DECIDED')
        decided_date = datetime.fromtimestamp(decided_result['dates'][0]).strftime('%m/%d/%Y')
        case_info.append(f'{decided_date}')
    else:
        case_info.append('DECIDED')
        case_info.append(NONE_VALUE)

    case_info.append('')

    for advocate in case_data['advocates']:
        case_info.append('ADVOCATE NAME')
        case_info.append(f'{advocate['advocate']['name']}')

        case_info.append('ADVOCATE LINK')
        case_info.append(f'https://www.oyez.org/advocates/{advocate['advocate']['identifier']}')

        case_info.append('ADVOCATE DESCRIPTION')
        case_info.append(f'{advocate['advocate_description']}')

        case_info.append('')


def format_case_data(case_data: Dict[str, Any]) -> List[str]:
    case_info = []

    format_basic_info(case_data, case_info)
    format_opinions(case_data, case_info)
    format_body(case_data, case_info)
    format_case_meta(case_data, case_info)

    return case_info


def main():
    details = parse_url()

    if details:
        process_case_data(details)


if __name__ == '__main__':
    main()
