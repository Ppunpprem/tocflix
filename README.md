🎬TOCFLIX

A movie browsing website built with Python Flask (backend) and React + Vite (frontend). Movie data is scraped from the IMDb Top 250 using a custom web crawler built with requests and BeautifulSoup4.

📋Prerequisites

Make sure you have the following installed:
Tool                  Version
Python                3.10 or higher
Node.js               20 or higher
npm                   9 or higher

📁 Project Structure

tocflix/
├── backend/
│   ├── imdb_movie_crawler.py   # Web crawler (scrapes IMDb Top 150)
│   ├── main.py                 # Flask API server
│   ├── requirements.txt        # Python dependencies
│   └── movies_cache.json       # Auto-generated cache (do not commit)
├── src/
│   ├── HomePage.jsx
│   ├── MoviesPage.jsx
│   ├── DetailPage.jsx
│   ├── Navbar.jsx
│   └── ...
├── public/
├── index.html
├── package.json
└── vite.config.js

🚀 How to Run Locally

1. Clone the repository
git clone https://github.com/Ppunpprem/tocflix.git
cd tocflix

2. Run the Backend (Flask)
cd backend
Install Python dependencies:
pip install -r requirements.txt
Start the Flask server:
python main.py

⏳ First run takes ~2 minutes — the crawler will scrape IMDb Top 150 movies and save a local cache (movies_cache.json).
✅ Subsequent runs load instantly from the cache.

The backend will be running at: http://127.0.0.1:5000

3. Run the Frontend (React + Vite)
Open a new terminal in the project root:
npm install
npm run dev
The frontend will be running at: http://localhost:5173/tocflix/

🔄 Re-crawl IMDb Data
If you want to refresh the movie data (e.g. after updating the crawler):
# Windows
del backend\movies_cache.json

# Mac / Linux
rm backend/movies_cache.json
Then restart the backend with python main.py.

🌐 API Endpoints
MethodEndpointDescriptionGET/moviesGet all movies (supports filters)GET/movies/<id>Get full detail for one movieGET/movies/trendingTop 10 highest ratedGET/movies/new-arrivalsTop 10 most recent

Query parameters for /movies:
ParamExampleDescriptionsearch?search=godfatherSearch by title, genre, countrygenre?genre=DramaFilter by genreyear?year=1994Filter by exact yearyear_from?year_from=2000Filter from yearyear_to?year_to=2010Filter to yearmin_rating?min_rating=8.5Filter by minimum IMDb ratingsort?sort=imdb_top10Return top 10 by rating

🛠 Tech Stack
Backend

Python 3.10+
Flask + Flask-CORS
BeautifulSoup4 (web scraping)
Requests
Gunicorn (for deployment)

Frontend

React 19
Vite
React Router DOM 7
Tailwind CSS

# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

the command for run everytimes

source venv/bin/activate
python backend/main.py  
npm run dev  