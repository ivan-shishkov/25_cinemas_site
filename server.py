from flask import Flask, render_template, jsonify
from flask_caching import Cache

from cinemas import get_top_rated_movies_info

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': 'cache'})


@cache.cached(timeout=3600, key_prefix='movies')
def get_movies_info(movies_count=10):
    return get_top_rated_movies_info(movies_count)


@app.route('/')
def films_list():
    movies_info = get_movies_info()

    return render_template('films_list.html', movies_info=movies_info)


@app.route('/api/top-rated-movies')
def top_rated_movies():
    return jsonify(top_rated_movies_info=get_movies_info())


if __name__ == "__main__":
    app.run()
