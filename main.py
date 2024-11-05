import json
import sys
from typing import Any, Dict, List
import os
import oyez_api_wrapper
from urllib.parse import urlparse


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

    file_path = f'oyez_{details['term']}_{details['docket']}.json'

    with open(file_path, 'r') as file:
        case_data = json.load(file)

        case_info = format_case_data(case_data)

        file_path = f'cases/case_{details['term']}_{details['docket']}.txt'

        with open(file_path, 'w') as file:
            file.write('\n'.join(case_info))

        # if os.path.exists(file_path):
        #     os.remove(file_path)

        print(f'{case_data['name']} retrieved')


def format_opinions(case_data: Dict, case_info: List[str]) -> None:
    if case_data['written_opinion'] == None:
        return
    
    syllabus_result = next(
        (opinion for opinion in case_data['written_opinion'] if opinion['type']['value'] == 'syllabus'), 
        None
    )

    if syllabus_result:
        case_info.append('VALUE')
        case_info.append(f'{syllabus_result['type']['label']}')
        case_info.append('LINK')
        case_info.append(f'{syllabus_result['justia_opinion_url']}')
    else:
        case_info.append('VALUE')
        case_info.append('')
        case_info.append('LINK')
        case_info.append('')

    case_info.append('')

    case_data['written_opinion'].remove(syllabus_result)

    case_info.append('OYEZ URL')
    case_info.append(case_data['href'].replace('api.', 'www.'))
    case_info.append('')

    majority_result = next(
        (opinion for opinion in case_data['written_opinion'] if opinion['type']['value'] == 'majority'), 
        None
    )

    if majority_result:
        case_info.append('JUSTICE')
        case_info.append(f'{majority_result['judge_full_name']}')
        case_info.append('TYPE OF OPINION')
        case_info.append(f'{majority_result['type']['label']}')
        case_info.append('LINK')
        case_info.append(f'{syllabus_result['justia_opinion_url']}')

        case_data['written_opinion'].remove(majority_result)
    else:
        case_info.append('JUSTICE')
        case_info.append('')
        case_info.append('TYPE OF OPINION')
        case_info.append('')
        case_info.append('LINK')
        case_info.append('')

    case_info.append('')

    for opinion in case_data['written_opinion']:
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
        case_info.append('')
    else:
        case_info.append(f'{case_data['decided_by']['name']}')
    case_info.append('')

    case_info.append('LOWER COURT')
    if case_data['lower_court'] == None:
        case_info.append('')
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
        case_info.append('')
    else:
        case_info.append('CITATION TEXT')
        case_info.append('')
        case_info.append('CITATION URL')
        case_info.append('')
        case_info.append('')


def format_case_data(case_data: Dict[str, Any]) -> List[str]:
    case_info = []

    case_info.append('TITLE')
    case_info.append(f'{case_data['name']}')
    case_info.append('')

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
