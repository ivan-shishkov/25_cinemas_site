from datetime import date
import re
from multiprocessing.pool import ThreadPool

import requests
from requests.exceptions import ConnectionError
from kinopoisk.movie import Movie


def fetch_json_content(url, params=None):
    headers = {
        'Accept': 'application/json',
    }
    try:
        response = requests.get(url, params=params, headers=headers)
        return response.json() if response.ok else None
    except ConnectionError:
        return None


def get_essential_afisha_movie_info(movie_info):
    return {
        'name': movie_info['Name'],
        'year': int(
            re.findall(r'\d+', movie_info['ProductionYear'])[0],
        ),
        'country': movie_info['Country'],
        'duration': movie_info['Duration'],
        'description': movie_info['Description'],
        'age_restriction': movie_info['AgeRestriction'],
        'afisha_url': 'https://www.afisha.ru{}'.format(
            movie_info['Url'],
        ),
        'screenshot_url': None if movie_info['Image315x315'] is None
        else movie_info['Image315x315']['Url']
    }


def get_afisha_movies_info(scheduled_date):
    page_number = 1

    while True:
        params = {
            'date': scheduled_date,
            'page': page_number,
        }
        afisha_movies_info_page = fetch_json_content(
            url='https://www.afisha.ru/msk/schedule_cinema/',
            params=params,
        )

        if afisha_movies_info_page is None:
            break

        yield [
            get_essential_afisha_movie_info(movie_info)
            for movie_info in afisha_movies_info_page['MovieList']['Items']
        ]

        if page_number >= afisha_movies_info_page['Pager']['PagesCount']:
            break

        page_number = page_number + 1


def get_normalized_movie_name(movie_name):
    return ' '.join(re.findall(r'\w+', movie_name.lower().replace('ё', 'е')))


def get_kinopoisk_movie_rating_info(afisha_movie_info):
    movie_rating = movie_votes = None

    normalized_afisha_movie_name = get_normalized_movie_name(
        afisha_movie_info['name'],
    )
    try:
        movies = Movie.objects.search(afisha_movie_info['name'])
    except ConnectionError:
        movies = []

    for movie in movies:
        normalized_movie_name = get_normalized_movie_name(
            movie.title,
        )
        if (movie.year == afisha_movie_info['year'] and
                normalized_movie_name == normalized_afisha_movie_name):
            movie_rating = movie.rating
            movie_votes = movie.votes

            break

    return {
        'rating': movie_rating,
        'votes': movie_votes,
    }


def add_kinopoisk_movie_rating_info(afisha_movie_info):
    movie_info = afisha_movie_info.copy()
    movie_info.update(get_kinopoisk_movie_rating_info(afisha_movie_info))

    return movie_info


def add_kinopoisk_movies_rating_info(afisha_movies_info):
    pool = ThreadPool(processes=8)

    movies_info = pool.map(add_kinopoisk_movie_rating_info, afisha_movies_info)

    return movies_info


def get_top_rated_movies_info(movies_count=10):
    scheduled_date = date.today().strftime('%d-%m-%Y')

    afisha_movies_info = []

    for afisha_movies_info_page in get_afisha_movies_info(scheduled_date):
        afisha_movies_info.extend(afisha_movies_info_page)

    movies_info = add_kinopoisk_movies_rating_info(afisha_movies_info)

    return sorted(
        movies_info,
        key=lambda movie: movie['rating'] if movie['rating'] else 0,
        reverse=True,
    )[:movies_count]
