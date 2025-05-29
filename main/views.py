import pickle
import os
import gzip
from django.conf import settings
import pandas as pd
import requests
from django.shortcuts import render

# Load movie list and similarity matrix
with open(os.path.join(settings.BASE_DIR, 'movie_list.pkl'), 'rb') as f:
    movies_dict = pickle.load(f)

movies = pd.DataFrame(movies_dict)

with open(os.path.join(settings.BASE_DIR, 'similarity.pkl.gz'), 'rb') as f:
    similarity = pickle.load(f)

# Function to fetch movie poster from TMDb
def fetch_poster(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        poster_path = data.get("poster_path")
        return f"https://image.tmdb.org/t/p/w500/{poster_path}" if poster_path else "https://via.placeholder.com/500x750?text=No+Poster"
    except Exception as e:
        print(f"[ERROR] fetch_poster({movie_id}):", e)
        return "https://via.placeholder.com/500x750?text=Error+Loading+Poster"

# Recommend function
def recommend(movie_title):
    try:
        movie_index = movies[movies['title'] == movie_title].index[0]
    except IndexError:
        return [], []

    distances = similarity[movie_index]
    movie_indices = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_titles = []
    recommended_posters = []

    for idx, _ in movie_indices:
        movie_id = movies.iloc[idx]['movie_id']  # make sure your DataFrame column is named 'movie_id'
        title = movies.iloc[idx]['title']
        poster_url = fetch_poster(movie_id)

        recommended_titles.append(title)
        recommended_posters.append(poster_url)

    return recommended_titles, recommended_posters

# Django view
def recommend_view(request):
    context = {
        'movies': movies['title'].values,
        'recommended': [],
        'selected_movie': ''
    }

    if request.method == "POST":
        selected_movie = request.POST.get("movie")
        titles, posters = recommend(selected_movie)
        context.update({
            'recommended': zip(titles, posters),
            'selected_movie': selected_movie
        })

    return render(request, "main/recommend.html", context)
