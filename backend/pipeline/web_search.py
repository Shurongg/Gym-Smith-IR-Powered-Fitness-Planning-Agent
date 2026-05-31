def web_search(query: str, max_results: int = 3) -> str:
    # The duckduckgo_search rename warning is muted by a warnings.warn patch in main.py
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        return "\n\n".join(
            f"Source: {r.get('href', '')}\nTitle: {r['title']}\n{r['body']}"
            for r in results
        )
    except Exception as e:
        return f"Search unavailable: {e}"
