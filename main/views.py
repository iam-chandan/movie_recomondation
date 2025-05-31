import pickle
import os
import gzip
from django.conf import settings
import pandas as pd
import httpx
from django.shortcuts import render
from asgiref.sync import sync_to_async

# Load movie list and similarity matrix (can remain sync)
with open(os.path.join(settings.BASE_DIR, 'movie_list.pkl'), 'rb') as f:
    movies_dict = pickle.load(f)

movies = pd.DataFrame(movies_dict)

with gzip.open(os.path.join(settings.BASE_DIR, 'similarity.pkl.gz'), 'rb') as f:
    similarity = pickle.load(f)

# Async fetch poster using httpx
async def fetch_poster(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US"
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            poster_path = data.get("poster_path")
            if poster_path:
                return f"https://image.tmdb.org/t/p/w500/{poster_path}"
            else:
                print(f"[INFO] No poster_path found for movie_id={movie_id}")
                return "https://via.placeholder.com/500x750?text=No+Poster"
        except httpx.HTTPStatusError as exc:
            print(f"[HTTP ERROR] {exc.response.status_code} for movie_id={movie_id}")
            return "https://via.placeholder.com/500x750?text=Error+Loading+Poster"
        except Exception as e:
            print(f"[ERROR] fetch_poster({movie_id}): {e}")
            return "https://via.placeholder.com/500x750?text=Error+Loading+Poster"


# sync recommend function (it uses pandas and your similarity matrix)
def recommend(movie_title):
    try:
        movie_index = movies[movies['title'] == movie_title].index[0]
    except IndexError:
        return [], []

    distances = similarity[movie_index]
    movie_indices = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_titles = []
    recommended_movie_ids = []

    for idx, _ in movie_indices:
        movie_id = movies.iloc[idx]['movie_id']
        title = movies.iloc[idx]['title']
        recommended_titles.append(title)
        recommended_movie_ids.append(movie_id)

    return recommended_titles, recommended_movie_ids

# Async Django view (Django 3.1+ supports async views)
async def recommend_view(request):
    context = {
        'movies': movies['title'].values,
        'recommended': [],
        'selected_movie': '',
        'selected_movie_poster': ''
    }

    if request.method == "POST":
        selected_movie = request.POST.get("movie")

        # Since recommend() uses pandas, which is sync, run it async using sync_to_async
        titles, movie_ids = await sync_to_async(recommend)(selected_movie)

        # Fetch posters asynchronously for recommended movies
        recommended_posters = []
        for movie_id in movie_ids:
            poster = await fetch_poster(movie_id)
            recommended_posters.append(poster)

        # Fetch poster for selected movie
        try:
            movie_id = movies[movies['title'] == selected_movie].iloc[0]['movie_id']
            selected_poster = await fetch_poster(movie_id)
        except Exception:
            selected_poster = "https://via.placeholder.com/500x750?text=Not+Found"

        context.update({
            'recommended': zip(titles, recommended_posters),
            'selected_movie': selected_movie,
            'selected_movie_poster': selected_poster
        })

    return render(request, "main/recommend.html", context)
