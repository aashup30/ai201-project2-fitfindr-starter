"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from tools import search_listings, suggest_outfit, create_fit_card, compare_price


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    import re

    # Step 1: Initialize session
    session = _new_session(query, wardrobe)
    print(f"\n{'='*60}")
    print(f"[AGENT] Starting new session for query: '{query}'")
    print(f"{'='*60}")

    # Step 2: Parse query for description, size, max_price
    size_match = re.search(r'\bsize\s+([A-Z0-9/]+)\b', query, re.IGNORECASE)
    price_match = re.search(r'under\s+\$?(\d+(?:\.\d+)?)', query, re.IGNORECASE)
    size = size_match.group(1) if size_match else None
    max_price = float(price_match.group(1)) if price_match else None
    description = re.sub(
        r'(size\s+[A-Z0-9/]+|under\s+\$?\d+|\$\d+|looking for|i\'?m looking for)',
        '', query, flags=re.IGNORECASE
    ).strip()
    session["parsed"] = {"description": description, "size": size, "max_price": max_price}
    print(f"\n[STEP 2] Parsed query:")
    print(f"  description : {description}")
    print(f"  size        : {size}")
    print(f"  max_price   : {max_price}")

    # Step 3: Search listings — exit early if nothing found
    print(f"\n[STEP 3] Calling search_listings('{description}', size={size}, max_price={max_price})")
    results = search_listings(description, size=size, max_price=max_price)
    session["search_results"] = results
    print(f"  → {len(results)} result(s) found")

    if not results:
        session["error"] = (
            "No listings matched your search. Try broadening your description, "
            "raising your price limit, or removing the size filter."
        )
        print(f"  ✗ No results — stopping early. Error set in session.")
        print(f"  session['fit_card'] = {session['fit_card']} (tools after search were NOT called)")
        return session

    # Step 4: Select top result
    session["selected_item"] = results[0]
    print(f"\n[STEP 4] Selected item stored in session['selected_item']:")
    print(f"  title : {session['selected_item']['title']}")
    print(f"  price : ${session['selected_item']['price']}")
    print(f"  id    : {session['selected_item']['id']}")

    # compare_price — always runs
    print(f"\n[STEP 4b] Calling compare_price() with session['selected_item'] (id={session['selected_item']['id']})")
    try:
        session["price_verdict"] = compare_price(session["selected_item"])
        print(f"  → verdict: {session['price_verdict']['verdict']}")
        print(f"  → {session['price_verdict']['reasoning']}")
    except Exception as e:
        session["price_verdict"] = None
        print(f"  ✗ compare_price failed: {e}")

    # Step 5: Suggest outfit
    print(f"\n[STEP 5] Calling suggest_outfit() with session['selected_item'] → '{session['selected_item']['title']}'")
    session["outfit_suggestion"] = suggest_outfit(session["selected_item"], wardrobe)
    print(f"  → outfit stored in session['outfit_suggestion']")
    print(f"  → preview: {session['outfit_suggestion'][:80]}...")

    # Step 6: Create fit card
    print(f"\n[STEP 6] Calling create_fit_card() with session['outfit_suggestion'] → passed in directly")
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], session["selected_item"])
    print(f"  → fit card stored in session['fit_card']")
    print(f"  → preview: {session['fit_card'][:80]}...")

    # Step 7: Return session
    print(f"\n[AGENT] Session complete. Keys set: selected_item, price_verdict, outfit_suggestion, fit_card")
    print(f"{'='*60}\n")
    return session

# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
