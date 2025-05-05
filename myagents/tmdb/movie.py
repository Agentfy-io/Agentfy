import requests
import json
from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    handoff,
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX


@function_tool(
    name_override="search_movies_tool", 
    description_override="Search for movies by title or keywords."
)
async def search_movies_tool(query: str, page: int = None, include_adult: bool = None, language: str = None) -> str:
    """
    Search for movies using The Movie Database (TMDB) API.
    
    Args:
        query: The movie title or keywords to search for.
        page: The page number of results to return.
        include_adult: Whether to include adult content in results.
        language: The language code for results.
        
    Returns:
        The movie search results as a string.
    """
    # Set default values inside function body
    if page is None:
        page = 1
    if include_adult is None:
        include_adult = False
    if language is None:
        language = "en-US"
        
    url = f"https://api.themoviedb.org/3/search/movie"
    
    params = {
        "query": query,
        "include_adult": str(include_adult).lower(),
        "language": language,
        "page": page
    }
    
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI5ZTA3ZDI0ZWVlZmRlMWUyOWY4YzQ1MzA3ZDVlM2RjYyIsIm5iZiI6MTcyNjQ3MTY2My41NDgzMTcsInN1YiI6IjY2ZTdkZDRlMDUwZjE0ZTRmY2NmZGJmMiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.JpRK3Tkh2nhwTnligGerWAhSIXcfbbeeTddH3ZuNNnA"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        result = response.json()
        
        # Extract the overview of the first movie if results exist
        if result.get("results") and len(result["results"]) > 0:
            first_movie = result["results"][0]
            title = first_movie.get("title", "No title available")
            overview = first_movie.get("overview", "No overview available")
            return f"Movie: {title}\n\nOverview: {overview}"
        else:
            return "No movies found matching your query."
    else:
        return f"Error searching for movies: {response.status_code} - {response.text}"


@function_tool(
    name_override="get_movie_details_tool", 
    description_override="Get detailed information about a movie by its ID."
)
async def get_movie_details_tool(movie_id: int) -> str:
    """
    Get detailed information about a movie from The Movie Database (TMDB) API.
    
    Args:
        movie_id: The ID of the movie to get details for.
        
    Returns:
        The movie details as a string.
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    
    params = {
        "append_to_response": "credits,videos,images,reviews"
    }
    
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI5ZTA3ZDI0ZWVlZmRlMWUyOWY4YzQ1MzA3ZDVlM2RjYyIsIm5iZiI6MTcyNjQ3MTY2My41NDgzMTcsInN1YiI6IjY2ZTdkZDRlMDUwZjE0ZTRmY2NmZGJmMiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.JpRK3Tkh2nhwTnligGerWAhSIXcfbbeeTddH3ZuNNnA"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        result = response.json()
        return json.dumps(result, indent=2)
    else:
        return f"Error getting movie details: {response.status_code} - {response.text}"


movie_agent = Agent(
    name="Movie Database Agent",
    handoff_description="A helpful agent that can search for movies and provide movie overviews.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a movie database agent. If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the movie-related query from the customer.
    2. If the customer is searching for a movie by title or keywords, use the search_movies_tool.
    3. If the customer wants detailed information about a specific movie and you have the movie ID, use the get_movie_details_tool.
    4. Present the movie information to the customer, focusing on providing the movie overview.
       - For search results, you'll receive the movie title and overview.
       - For movie details, highlight the most important information like plot summary, cast, and ratings.
    5. If you cannot find the requested movie or provide the information, transfer back to the triage agent.""",
    tools=[search_movies_tool, get_movie_details_tool],
)
