import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any, Union
from urllib.parse import quote

from tweepy.api import pagination

# Constants
API_KEY = "YOUR_API_KEY"  # Replace with your actual RapidAPI key
API_HOST = "linkedin-api8.p.rapidapi.com"
BASE_URL = f"https://{API_HOST}"
HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": API_HOST,
    "Content-Type": "application/json"
}
RATE_LIMIT_DELAY = 1  # Seconds between requests to avoid rate limiting


async def _make_get_request(endpoint: str, params: Optional[Dict] = None) -> Dict:
    """Make an async GET request to the LinkedIn API."""
    url = f"{BASE_URL}{endpoint}"
    query_params = {}
    if params:
        # Convert params to query string parameters
        for key, value in params.items():
            if value is not None:
                query_params[key] = value

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, params=query_params) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        print(f"Request error: {e}")
        return {"error": str(e)}


async def _make_post_request(endpoint: str, data: Dict) -> Dict:
    """Make an async POST request to the LinkedIn API."""
    url = f"{BASE_URL}{endpoint}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=HEADERS, json=data) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        print(f"Request error: {e}")
        return {"error": str(e)}


async def get_profile_by_username(username: str) -> List[Dict]:
    """
    Get LinkedIn profile information by username.

    Args:
        username: LinkedIn username
    """
    param = {
        "username": username
    }
    result = await _make_get_request("/get-profile-data", param)
    return [result]


async def get_profile_by_url(url: str) -> List[Dict]:
    """
    Get LinkedIn profile information by profile URL.

    Args:
        url: LinkedIn profile URL
    """
    param = {
        "url": url
    }
    result = await _make_get_request("/get-profile-data-by-url", param)
    return [result]


async def search_people_detailed(keywords: Optional[str] = None,
                                 start: Optional[int] = 0,
                                 geo: Optional[str] = None,
                                 school_id: Optional[str] = None,
                                 first_name: Optional[str] = None,
                                 last_name: Optional[str] = None,
                                 keyword_school: Optional[str] = None,
                                 keyword_title: Optional[str] = None,
                                 company: Optional[str] = None) -> List[Dict]:
    """
    Search for LinkedIn profiles with detailed filtering options.
    At least one search parameter must be provided.

    Args:
        keywords: Search keywords
        start: Starting index for pagination
        geo: Geographic location codes (comma-separated)
        school_id: School ID filter
        first_name: Filter by first name
        last_name: Filter by last name
        keyword_school: Filter by school keywords
        keyword_title: Filter by job title keywords
        company: Filter by company name
    """
    if not keywords and not geo and not school_id and not first_name and not last_name and not keyword_school and not keyword_title and not company:
        raise ValueError("At least one search parameter must be provided.")

    params = {
        "keywords": keywords,
        "start": start,
        "geo": geo,
        "school_id": school_id,
        "first_name": first_name,
        "last_name": last_name,
        "keyword_school": keyword_school,
        "keyword_title": keyword_title,
        "company": company
    }

    result = await _make_get_request("/search-people", params)
    return result.get("data",{}).get("items",[])

async def search_people_by_url(search_url: str) -> List[Dict]:
    """
    Search for LinkedIn profiles using a LinkedIn search URL.

    Args:
        search_url: LinkedIn search URL
    """
    data = {"url": search_url}

    result = await _make_post_request("/search-people-by-url", data)
    return result.get("data",{}).get("items",[])


async def get_profile_recent_activity_time(username: str) -> Dict:
    """
    Get the time of a user's most recent activity time. For example, like 11H ago.

    Args:
        username: LinkedIn username
    """
    return await _make_get_request(f"/get-profile-recent-activity-time?username={username}")


async def get_profile_posts(username: str, max_pages: Optional[int] = 1, postedAt: Optional[str] = None) -> List[Dict]:
    """
    Get posts from a LinkedIn profile.

    Args:
        username: LinkedIn username
        max_pages: Maximum number of posts to return
        postedAt: Date filter for posts, It is not an official filter. It filters posts after fetching them from LinkedIn and returns posts that are newer than the given date. Example value: 2024-01-01 00:00
    """
    params = {
        "username": username,
        "postedAt": postedAt
    }
    all_posts = []
    next_token = None

    for _ in range(max_pages):
        params["paginationToken"] = next_token
        result = await _make_get_request("/get-profile-posts", params)
        all_posts.extend(result.get("data", []))

        # Check if there are more pages
        next_token = result.get("paginationToken")
        if not next_token:
            break

    return all_posts


async def get_post_comments(urn: str, sort: str = "mostRelevant", max_pages: Optional[int] = 1) -> List[Dict]:
    """
    Get comments on a specific LinkedIn post.

    Args:
        urn: Post URN identifier
        sort: Sort method ("mostRelevant" or "mostRecent")
        max_pages: Maximum number of pages to fetch
    """
    params = {
        "urn": urn,
        "sort": sort,
    }
    all_posts = []
    next_token = None

    for _ in range(max_pages):
        params["paginationToken"] = next_token
        result = await _make_get_request("/get-post-comments", params)
        all_posts.extend(result.get("data", []))

        # Check if there are more pages
        next_token = result.get("paginationToken")
        if not next_token:
            break

    return all_posts


async def get_profile_comments(username: str) -> List[Dict]:
    """
    Get comments made by a LinkedIn profile.

    Args:
        username: LinkedIn username
    """
    params = {
        "username": username
    }
    result = await _make_get_request("/get-profile-comments", params)
    return result.get("data", [])


async def get_connection_and_follower_count(username: str) -> List[Dict]:
    """
    Get the connection count for a LinkedIn profile.

    Args:
        username: LinkedIn username
    """
    param = {
        "username": username
    }
    result = await _make_get_request("/get-connection-and-follower-count", param)
    data = result.get("data", {})
    data["connection"] = result["connection"]
    data["follower"] = result["follower"]
    return [data]


async def get_given_recommendations(username: str) -> List[Dict]:
    """
    Get recommendations given by a LinkedIn profile.

    Args:
        username: LinkedIn username
    """
    params = {
        "username": username,
    }

    result = await _make_get_request("/get-given-recommendations", params)
    return result.get("data", {}).get("items", [])


async def get_received_recommendations(username: str) -> List[Dict]:
    """
    Get recommendations received by a LinkedIn profile.

    Args:
        username: LinkedIn username
    """
    params = {
        "username": username,
    }

    result = await _make_get_request("/get-received-recommendations", params)
    return result.get("data", {}).get("items", [])


async def get_profile_likes(username: str, max_pages: Optional[int] = 1) -> List[Dict]:
    """
    Get posts liked list by a LinkedIn profile.

    Args:
        username: LinkedIn username
        max_pages: Maximum number of pages to fetch
    """
    params = {
        "username": username,
    }
    all_likes = []
    next_token = None

    for _ in range(max_pages):
        params["paginationToken"] = next_token
        result = await _make_get_request("/get-profile-likes", params)
        all_likes.extend(result.get("data", {}).get("items", []))

        # Check if there are more pages
        next_token = result.get("data", {}).get("paginationToken", [])
        if not next_token:
            break

    return all_likes


async def get_profile_data_connection_count_posts(username: str) -> [Dict]:
    """
    Get combined profile data, connection count, and posts.

    Args:
        username: LinkedIn username
    """
    params = {
        "username": username,
    }
    result = await _make_get_request("/profile-data-connection-count-posts", params)
    return [result]


async def get_similar_profiles(url: str) -> List[Dict]:
    """
    Get profiles similar to a given LinkedIn profile.

    Args:
        url: LinkedIn profile URL
    """
    params = {
        "url": url
    }
    result = await _make_get_request("/similar-profiles", params)
    return result.get("data", {}).get("items", [])


async def linkedin_to_email(url: str) -> Dict:
    """
    Attempt to find an email address associated with a LinkedIn profile.

    Args:
        url: LinkedIn profile URL
    """
    if not url.startswith("https://www.linkedin.com/in/"):
        raise ValueError("Invalid LinkedIn profile URL. Must start with 'https://www.linkedin.com/in/'")

    return await _make_get_request(f"/linkedin-to-email?url={quote(url)}")


async def get_company_details_by_username(username: str) -> List[Dict]:
    """
    Get company details for a LinkedIn profile.

    Args:
        username: company LinkedIn username
    """
    param = {
        "username": username
    }
    result = await _make_get_request("/get-company-details", param)
    return [result.get("data", {})]


async def get_company_details_by_id(company_id: str) -> List[Dict]:
    """
    Get company details for a LinkedIn profile by company ID.

    Args:
        company_id: company LinkedIn ID
    """
    param = {
        "id": company_id
    }
    result = await _make_get_request("/get-company-details", param)
    return [result.get("data", {})]


async def get_company_jobs(company_id: int, sort: str = "mostRecent", max_pages: Optional[int] = 1) -> List[Dict]:
    """
    Get job listings from specific companies.

    Args:
        company_id: LinkedIn company ID
        sort: Sort method ("mostRecent" or other options)
        max_pages: Maximum number of pages to fetch
    """
    data = {
        "companyIds": [company_id],
        "sort": sort
    }
    all_jobs = []
    page = 1

    for _ in range(max_pages):
        data["page"] = page
        result = await _make_post_request("/get-company-jobs", data)
        all_jobs.extend(result.get("data", {}).get("items", []))

        page += 1

    return all_jobs


async def get_company_by_domain(domain: str) -> List[Dict]:
    """
    Get company information by domain name.

    Args:
        domain: Company domain name (e.g., "apple.com")
    """
    result = await _make_get_request("/get-company-by-domain", {"domain": domain})
    return [result.get("data", {})]


async def search_companies(keyword: Optional[str] = "",
                           location_ids: Optional[List[int]] = None,
                           company_sizes: Optional[List[str]] = None,
                           has_jobs: bool = False,
                           industry_ids: Optional[List[int]] = None,
                           max_pages: Optional[int] = 1) -> List[Dict]:
    """
    Search for companies with various filters.

    Args:
        keyword: Search keyword
        location_ids: List of location IDs
        company_sizes: List of company size codes (e.g., ["D", "E", "F", "G"])
        has_jobs: Filter for companies with active job listings
        industry_ids: List of industry IDs
        max_pages: Maximum number of pages to fetch
    """
    data = {
        "keyword": keyword,
        "locations": location_ids,
        "companySizes": company_sizes,
        "hasJobs": has_jobs,
        "industries": industry_ids
    }
    page = 1
    all_companies = []

    for _ in range(max_pages):
        data["page"] = page

        result = await _make_post_request("/search-companies", data)
        all_companies.extend(result.get("data", {}).get("items", []))

        if not all_companies:
            break

        page += 1

    return all_companies


async def get_company_employees_count(company_id: str, locations: Optional[List[int]] = None) -> List[Dict]:
    """
    Get the number of employees at a company.

    Args:
        company_id: LinkedIn company ID
        locations: Optional list of location IDs to filter by
    """
    data = {
        "companyId": company_id,
        "locations": locations or []
    }

    result = await _make_get_request("/get-company-employees-count", data)
    by_groups = result.get("data", {}).get("byGroups", {})
    by_groups["total"] = result.get("data", {}).get("total", 0)

    return [by_groups]


async def get_company_total_jobs_count(company_id: str) -> int:
    """
    Get the number of jobs at a company.

    Args:
        company_id: LinkedIn company ID
    """
    result = await _make_get_request("/get-company-jobs-count", {"companyId": company_id})
    return result.get("data", {}).get("total", 0)


async def get_company_posts(username: str, max_pages: Optional[int] = 1) -> List[Dict]:
    """
    Get posts from a company's LinkedIn page.

    Args:
        username: Company's LinkedIn username
        max_pages: Maximum number of pages to fetch
    """
    params = {
        "username": username,
    }
    start = 0
    pagination_token = None
    all_posts = []

    for _ in range(max_pages):
        params["start"] = start
        params["paginationToken"] = pagination_token
        result = await _make_get_request("/get-company-posts", params)
        start += 50

        if start + 1 > result.get("totalPages", 0):
            break

        all_posts.extend(result.get("data", []))
        pagination_token = result.get("paginationToken")

    return all_posts

async def get_company_post_comments(urn: str, sort: str = "mostRelevant", max_pages: Optional[int] = 1) -> List[Dict]:
    """
    Get comments on a company's LinkedIn post.

    Args:
        urn: Post URN identifier
        sort: Sort method ("mostRelevant" or "oldest")
        max_pages: Maximum number of pages to fetch
    """
    params = {
        "urn": urn,
        "sort": sort,
    }
    page = 1
    all_posts = []

    for _ in range(max_pages):
        params["page"] = page
        result = await _make_get_request("/get-company-post-comments", params)
        all_posts.extend(result.get("data", []))

        if page + 1 > result.get("totalPages", 0):
            break
        page += 1

    return all_posts


async def search_jobs(keywords: str,
                      location_id: Optional[str] = None,
                      companyIds: Optional[List[str]] = None,
                      date_posted: str = "anyTime",
                      salary: Optional[str] = None,
                      job_type: Optional[str] = None,
                      experience_level: Optional[str] = None,
                      title_ids: Optional[List[str]] = None,
                      industry_ids: Optional[List[str]] = None,
                      onsiteRemote: Optional[str] = None,
                      sort: str = "mostRelevant",
                      distance: Optional[str] = None) -> List[Dict]:
    """
    Search for job listings on LinkedIn, only top 50 results are returned.

    Args:
        keywords: Job search keywords
        location_id: Location ID
        companyIds: List of company IDs fullTime, partTime, contract, internship
        salary: Salary filter (40k+, 60k+, 80k+, 100k+, 120k+, 140k+, 160k+, 180k+, 200k+)
        job_type: Job type filter (fullTime, partTime, contract, internship)
        experience_level: Experience level filter (e.g.,internship, associate, director, entryLevel, midSeniorLeve)
        title_ids: List of job title IDs
        industry_ids: List of industry IDs
        onsiteRemote: Onsite/remote filter ("onSite", "remote", "hybrid")
        date_posted: Time filter ("anyTime", "past24Hours", "pastWeek", "pastMonth")
        sort: Sort method ("mostRelevant", "mostRecent")
        distance: Distance filter (0 = 0km, 5 = 8km, 10 = 16km, 25 = 40km, 50 = 80km, 100 = 160km)
    """
    params = {
        "keywords": keywords,
        "companyIds": companyIds,
        "datePosted": date_posted,
        "salary": salary,
        "jobType": job_type,
        "experienceLevel": experience_level,
        "titleIds": title_ids,
        "industryIds": industry_ids,
        "onsiteRemote": onsiteRemote,
        "distance": distance,
        "sort": sort
    }

    result = await _make_get_request(f"/search-jobs?locationId={location_id}", params)

    return result.get("data", [])


async def get_hiring_team(job_id: Optional[str] = None, job_url: Optional[str] = None) -> List[Dict]:
    """
    Get information about the hiring team for a job listing, such as the recruiter info.

    Args:
        job_id: LinkedIn job ID
        job_url: Optional LinkedIn job listing URL
    """
    if not job_id and not job_url:
        raise ValueError("Either job_id or job_url must be provided.")

    params = {}
    if job_id:
        params["jobId"] = job_id
    elif job_url:
        params["url"] = job_url

    result = await _make_get_request("/get-hiring-team", params)

    return result.get("data", {}).get("items", [])


async def save_to_json(data: Any, filename: str) -> None:
    """Save data to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Data saved to {filename}")



# Example usage
async def main():
    start = time.time()

    # Example: Get profile by username
    profile = await get_profile_by_username("adamselipsky")
    await save_to_json(profile, "linkedin_profile.json")

    # Example: Get profile posts
    posts = await get_profile_posts("adamselipsky")
    await save_to_json(posts, "linkedin_posts.json")

    # Example: Search for people
    search_results = await search_people("max", start=0, geo="103644278,101165590")
    await save_to_json(search_results, "linkedin_search.json")

    # Example: Get all profile data
    full_profile = await get_all_profile_data("ryanroslansky")
    await save_to_json(full_profile, "linkedin_full_profile.json")

    # Example: Running multiple operations concurrently
    tasks = [
        get_profile_by_url("https://www.linkedin.com/in/adamselipsky/"),
        get_connection_count("adamselipsky"),
        get_about_this_profile("williamhgates")
    ]

    results = await asyncio.gather(*tasks)
    profile_by_url, connection_count, about_profile = results

    await save_to_json(profile_by_url, "linkedin_profile_by_url.json")
    await save_to_json(connection_count, "linkedin_connections.json")
    await save_to_json(about_profile, "linkedin_about.json")

    print(f"Total time: {time.time() - start:.2f}s")


# Running the async main function
if __name__ == "__main__":
    asyncio.run(main())