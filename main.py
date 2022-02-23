import requests
import os
from itertools import count
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


def get_average_salary(lower_limit, upper_limit):
    if not lower_limit or lower_limit == 0:
        return 0.8*upper_limit
    elif not upper_limit or upper_limit == 0:
        return 1.2*lower_limit
    else:
        return (lower_limit + upper_limit) / 2


def get_average_salaries(salaries):
    if len(salaries) == 0:
        return 0
    return sum(salaries)//len(salaries)


def predict_rub_salary_hh(vacancy):
    if not vacancy['salary'] or vacancy['salary']['currency'] != 'RUR':
        return None

    lower_limit = vacancy['salary'].get('from', None)
    upper_limit = vacancy['salary'].get('to', None)

    if vacancy['salary']['gross']:
        return 0.87*get_average_salary(lower_limit, upper_limit)

    return get_average_salary(lower_limit, upper_limit)


def predict_rub_salary_sj(vacancy):
    if (vacancy['payment_from'] == 0 and vacancy['payment_to'] == 0) or \
            vacancy['currency'] != 'rub':
        return None

    return get_average_salary(vacancy['payment_from'], vacancy['payment_to'])


def get_hh_statistics(url_hh, language):
    params = {
        'text': 'name:Программист {}'.format(language),
        'area': 1,
        'period': 30,
        'per_page': 20,
    }

    language_vacancies = []
    counter = count()
    for page in counter:
        page = page
        params['page'] = page
        response = get_response(url_hh, params=params)
        language_vacancies.append(response)

        salaries = get_salaries(
            language_vacancies,
            'items',
            predict_rub_salary_hh
        )

        language_stats = {
            'vacancies_found': response['found'],
            'vacancies_processed': len(salaries),
            'average_salary': get_average_salaries(salaries)
        }

        if page + 1 > response['pages'] or page == 99:
            break

    return language_stats


def get_sj_statistics(url_sj, language, sj_key):
    headers = {'X-Api-App-Id': sj_key}
    params = {
        'keyword': 'Программист {}'.format(language),
        'town': 'Москва',
    }

    language_vacancies = []
    counter = count()
    for page in counter:
        page = page
        params['page'] = page
        response = get_response(url_sj, headers=headers, params=params)
        language_vacancies.append(response)

        salaries = get_salaries(
            language_vacancies,
            'objects',
            predict_rub_salary_sj
        )

        language_stats = {
            'vacancies_found': response['total'],
            'vacancies_processed': len(salaries),
            'average_salary': get_average_salaries(salaries)
        }

        if not response['more']:
            break

    return language_stats


def create_table(statistics):
    salary_statistics = [[
        'Язык программирования',
        'Найдено вакансий',
        'Обработано вакансий',
        'Средняя зарплата',
    ]]

    for language, statistics in statistics.items():
        salary_statistics.append([
            language,
            statistics['vacancies_found'],
            statistics['vacancies_processed'],
            statistics['average_salary'],
        ])

    return salary_statistics


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

    hh_statistics, sj_statistics = {}, {}
    for language in languages:
        hh_statistics[language] = get_hh_statistics(url_hh, language)
        sj_statistics[language] = get_sj_statistics(url_sj, language, sj_key)

    print(AsciiTable(create_table(hh_statistics), 'HeadHunter Moscow').table)
    print(AsciiTable(create_table(sj_statistics), 'SuperJob Moscow').table)

if __name__ == '__main__':
    main()
