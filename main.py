import requests
import os
from terminaltables import AsciiTable
from dotenv import load_dotenv


def get_response(url, headers=None, params=None):
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def get_salaries(vacancies, key, salary_func):
    salaries = []
    for vacancy_batch in vacancies:
        for vacancy in vacancy_batch[key]:
            salary = salary_func(vacancy)
            if salary:
                salaries.append(salary)
    return salaries


def predict_rub_salary_hh(vacancy):
    if not vacancy['salary'] or vacancy['salary']['currency'] != 'RUR':
        return None
    else:
        lower_limit = vacancy['salary'].get('from', None)
        upper_limit = vacancy['salary'].get('to', None)

        if not lower_limit:
            lower_limit = 0.6*upper_limit
        if not upper_limit:
            upper_limit = 1.4*lower_limit

        if vacancy['salary']['gross']:
            return 0.87*(lower_limit+upper_limit)/2
        else:
            return (lower_limit + upper_limit) / 2


def predict_rub_salary_sj(vacancy):
    if (vacancy['payment_from'] == 0 and vacancy['payment_to'] == 0) or \
            vacancy['currency'] != 'rub':
        return None
    elif vacancy['payment_from'] == 0:
        return 0.8*vacancy['payment_to']
    elif vacancy['payment_to'] == 0:
        return 1.2*vacancy['payment_from']
    else:
        return (vacancy['payment_from'] + vacancy['payment_to'])/2


def get_hh_statistic(url_hh, languages):
    vacancies = {}
    for language in languages:
        language_stats = {}

        params = {
            'text': 'name:Программист {}'.format(language),
            'area': 1,
            'period': 30,
        }
        response = get_response(url_hh, params=params)
        language_stats['vacancies_found'] = response['found']
        pages = response['pages']

        language_vacancies = []
        for page in range(pages):
            params = {
                'text': 'name:Программист {}'.format(language),
                'area': 1,
                'period': 30,
                'per_page': 20,
                'page': page,
            }
            response = get_response(url_hh, params=params)
            language_vacancies.append(response)

        salaries = get_salaries(
            language_vacancies,
            'items',
            predict_rub_salary_hh
        )

        language_stats['vacancies_processed'] = len(salaries)
        language_stats['average_salary'] = int(sum(salaries)/len(salaries))

        vacancies[language] = language_stats

    return vacancies


def get_sj_statistic(url_sj, languages, sj_key):
    vacancies = {}
    for language in languages:
        language_stats = {}

        headers = {'X-Api-App-Id': sj_key}
        params = {
            'keyword': 'Программист {}'.format(language),
            'town': 'Москва',
        }
        response = get_response(url_sj, headers=headers, params=params)

        if response['total'] > 0:
            language_stats['vacancies_found'] = response['total']
            pages = response['total']//20 + 1

            language_vacancies = []
            for page in range(pages):
                params = {
                    'keyword': 'Программист {}'.format(language),
                    'town': 'Москва',
                    'page': page,
                }
                response = get_response(url_sj, headers=headers, params=params)
                language_vacancies.append(response)

                salaries = get_salaries(
                    language_vacancies,
                    'objects',
                    predict_rub_salary_sj
                )

            language_stats['vacancies_processed'] = len(salaries)
            language_stats['average_salary'] = int(sum(salaries)/len(salaries))

            vacancies[language] = language_stats

    return vacancies


def show_tables(statistic, title):
    table_data = []
    table_data.append([
        'Язык программирования',
        'Найдено вакансий',
        'Обработано вакансий',
        'Средняя зарплата',
    ])

    for key, value in statistic.items():
        table_data.append([
            key,
            value['vacancies_found'],
            value['vacancies_processed'],
            value['average_salary'],
        ])

    table = AsciiTable(table_data, title)
    print(table.table)


def main():
    load_dotenv()
    sj_key = os.getenv("SUPERJOB_KEY")

    languages = [
        'TypeScript',
        'Swift',
        'Scala',
        'Objective-C',
        'Go',
        'C',
        'C#',
        'C++',
        'PHP',
        'Ruby',
        'Python',
        'Java',
        'JavaScript',
    ]

    url_hh = 'https://api.hh.ru/vacancies'
    url_sj = 'https://api.superjob.ru/2.0/vacancies'

    hh_statistic = get_hh_statistic(url_hh, languages)
    sj_statistic = get_sj_statistic(url_sj, languages, sj_key)

    show_tables(hh_statistic, 'HeadHunter Moscow')
    show_tables(sj_statistic, 'SuperJob Moscow')

if __name__ == '__main__':
    main()