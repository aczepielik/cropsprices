from typing import Any, Dict, List, Optional

import requests  # type: ignore


class PagedAPIQuery:
    def __init__(self, base_url: str, params: Optional[Dict[str, Any]] = None):
        self.base_url = base_url
        self.params = params or {}

    def get_page(self, page: int) -> Dict[str, Any]:
        """
        Fetch a single page of data from the API.

        Args:
            page (int): The page number to fetch.

        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        params = {**self.params, "page": page}
        response = requests.get(self.base_url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()

    def get_all_pages(self) -> List[Dict[str, Any]]:
        """
        Fetch all pages of data from the API.

        Returns:
            List[Dict[str, Any]]: A list of all pages of data.
        """
        all_data = []
        page = 1
        while True:
            data = self.get_page(page)
            all_data.append(data)
            if not self.has_next_page(data):
                break
            page += 1
        return all_data

    def has_next_page(self, data: Dict[str, Any]) -> bool:
        """
        Check if there is a next page of data.

        Args:
            data (Dict[str, Any]): The current page of data.

        Returns:
            bool: True if there is a next page, False otherwise.
        """
        return "next" in data.get("links", {})


def query_paged_api(
    url: str, params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Query a paged API and return all results.

    Args:
        url (str): The base URL of the API.
        params (Optional[Dict[str, Any]]): Additional parameters for the API request.

    Returns:
        List[Dict[str, Any]]: A list of all pages of data from the API.
    """
    api_query = PagedAPIQuery(url, params)
    return api_query.get_all_pages()
