# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**

This tool will search secondhand listings online to find relevant items to display and feed to the next tools. It should be able to feed correct input for later on if no relevant matches can be found.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): description of the item being searched like "vintage graphic tee" or "oversized denim jacket". Used to match against listing titles, descriptions, and style tags.
- `size` (str): Clothing size to look for. Examples include: "M", "L", "XS". Matched against the size field in listings. If omitted or None, don't use size as a filter.
- `max_price` (float): Upper price limit in US Dollars. Only listings priced at or below this value are returned. If omitted or None, no price ceiling is applied.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
A ranked list of listing objects, each containing: id, title, price, size, condition, platform, style_tags, and colors. Sorted by relevance to the description. Returns an empty list if nothing matches.


**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
If the list is empty, the agent tells the user nothing matched and suggests adjustments (broaden the description, raise the price limit, or remove the size filter). It does not pass empty results to suggest_outfit. 

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given a specific secondhand item and the user's current wardrobe, suggests one or more complete outfit combinations and styling notes on how to wear the item.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): A single listing object returned by search_listings and contains fields such as title, style_tags, colors, and category.
- `wardrobe` (dict): The user's existing wardrobe following wardrobe_schema.json and contains items grouped by category (tops, bottoms, shoes, etc.) with fields like style, color, and fit

**What it returns:**
<!-- Describe the return value -->
A list of one outfit suggestion containing the following: a combination (list of wardrobe items paired with the new item) and styling_notes (a short string describing how to wear the look).

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If the wardrobe is empty, the agent asks the user to describe a few pieces they already own before retrying. If the wardrobe is too sparse to form a complete outfit, the agent returns a partial suggestion with a note that more wardrobe items would improve results. 

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This tool will generate a short, shareable caption for the complete outfit with the style tips. Output should feel personal, not like a product description.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (dict): A single outfit suggestion from the previous suggest outfit tool that contains combination (list of items) and styling_notes and the new_item object (with fields title, price, platform, and style_tags) pulled in from search_listings.

**What it returns:**
<!-- Describe the return value -->
A 1–2 sentence caption that mentions the thrifted item, how it fits into the outfit, and has a personal tone.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->

If the outfit data is incomplete (e.g., missing combination or styling_notes), the agent falls back to generating a minimal caption using just the item title and price from the new_item stored in the outfit dict. 

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->
### Tool 4: compare_price

**What it does:**
Given a listing, estimates whether its price is fair by comparing it against similar items in the dataset. Returns a verdict and context to help the user decide if it's worth buying.

**Input parameters:**
- `item` (dict): A single listing object from search_listings that contains title, price, category, style_tags, condition, and brand. Used to find comparable listings and benchmark the price.

**What it returns:**
A dict containing: verdict (one of "great deal", "fair", or "overpriced"), avg_comparable_price (float), comparable_count (int — how many similar listings were found), and a short reasoning string explaining the verdict.

**What happens if it fails or returns nothing:**
If fewer than 2 comparable listings exist in the dataset, the agent tells the user there isn't enough data to make a reliable comparison and skips the verdict. If there is another error, fitfindr catches the exception and continues without a price verdict and the user is informed but the rest of the interaction is unaffected.
---


## Planning Loop

**How does your agent decide which tool to call next?**

The agent runs a sequential loop with early exits at each step based on what was returned.

**Step 1 — search_listings:**
Always runs first. After it returns, check if `results` is empty.
- If empty: set `session["error"] = "no listings found"`, send the message to the user, and return early. Do not proceed.
- If not empty: set `session["selected_item"] = results[0]` and continue.

**Step 2 — compare_price (optional):**
Runs if `session["selected_item"]` exists and the user asked about price or value.
- If `comparable_count < 2`: skip the verdict, note it in session, continue.
- If successful: set `session["price_verdict"] = verdict` and continue.

**Step 3 — suggest_outfit:**
Runs if `session["selected_item"]` exists.
Check if `wardrobe` has at least one item.
- If empty: ask the user to describe some pieces they own, wait for input, then retry.
- If not empty: call `suggest_outfit(new_item=session["selected_item"], wardrobe=wardrobe)`, set `session["outfit"] = results[0]`, and continue.

**Step 4 — create_fit_card:**
Runs if `session["outfit"]` exists.
- If outfit is missing `combination` or `styling_notes`: generate a minimal caption from `session["selected_item"]` fields only.
- If successful: set `session["fit_card"] = caption` and return the final output to the user.

**When is the agent done?**
When `session["fit_card"]` is set, or when an unrecoverable error is set and indicated to the user.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->


The agent maintains a `session` dict that persists for the duration of a single interaction. Each tool writes its output to a named key in `session`, and the next tool reads from it rather than taking direct return values as arguments. This allows tools to be tested in isolation.

Keys tracked in session:
- `session["results"]` — full list returned by `search_listings`
- `session["selected_item"]` — the top result from `search_listings`, passed to `compare_price` and `suggest_outfit`
- `session["price_verdict"]` — verdict dict from `compare_price`, included in the final output if available
- `session["outfit"]` — top outfit suggestion from `suggest_outfit`, passed to `create_fit_card`
- `session["fit_card"]` — final caption string from `create_fit_card`
- `session["error"]` — set if any tool fails or returns nothing useful; checked before each subsequent tool call

---

## Error Handling
| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets `session["error"]`, tells the user nothing matched and suggests adjustments (broaden description, raise price limit, remove size filter), returns early without calling further tools |
| compare_price | Fewer than 2 comparable listings found | Skips the verdict, notes in session that price data was unavailable, and continues to `suggest_outfit` — user is informed in the final output |
| suggest_outfit | Wardrobe is empty | Pauses the loop, asks the user to describe a few pieces they own, updates the wardrobe with their response, then retries the tool |
| create_fit_card | Outfit input is missing or incomplete | Falls back to generating a minimal caption using only the `title`, `price`, and `platform` fields from `session["selected_item"]` |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

## Architecture

```
User query
    │
    ▼
Planning Loop ◄──────────────────────────────────────────────────────┐
    │                                                                 │
    ├─► search_listings(description, size, max_price)                 │
    │       │                                                         │
    │       ├── results=[] ──► [ERROR] "Nothing matched — try         │
    │       │                   broader description, higher price,    │
    │       │                   or remove size filter." ──► STOP      │
    │       │                                                         │
    │       └── results=[item, ...] ──► Session: results,             │
    │                                            selected_item        │
    │                                       │                         │
    ├─► compare_price(selected_item)        │                         │
    │       │                              │                          │
    │       ├── comparable_count < 2 ──► skip verdict, continue       │
    │       │                                                         │
    │       └── verdict found ──► Session: price_verdict              │
    │                                       │                         │
    ├─► suggest_outfit(selected_item, wardrobe)                       │
    │       │                                                         │
    │       ├── wardrobe=[] ──► ask user for wardrobe details ────────┘
    │       │                  (retry with updated wardrobe)
    │       │
    │       └── suggestions=[...] ──► Session: outfit
    │                                       │
    └─► create_fit_card(outfit)             │
            │                              │
            ├── outfit incomplete ──► fallback: minimal caption
            │                        from selected_item fields
            │
            └── success ──► Session: fit_card
                                    │
                                    ▼
                            Final output to user:
                            selected_item + price_verdict
                            + outfit suggestion + fit_card
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 1&2 — Planning and Scope:** 
I used AI to refine what I wrote and think of extra failure cases. I also wrote out my planning loop in plain words and asked AI to create the diagram based on it itself.

**Milestone 3 — Individual tool implementations:**

I'll use Claude for each tool. For each, I'll paste the corresponding Tool spec block from planning.md (what it does, input parameters, return value, failure mode) along with additional context like what's included in tools.py.

- For `search_listings`: I'll give Claude the Tool 1 information from planning.md and ask it to implement the function using `load_listings()` from `utils/data_loader.py`. I'll verify by running the three pytest cases (returns results, returns empty list, respects price filter) and checking that the empty-list case returns `[]` without raising an exception.
- For `compare_price`: I'll give Claude the Tool 4 spec and ask it to implement the function using `load_listings()` to find comparable items by matching category and style_tags. I'll verify by calling it with a listing that has clear comparables and confirming the verdict and `avg_comparable_price` are reasonable, then calling it with a niche item that has fewer than 2 comparables and confirming it returns a "not enough data" message rather than crashing.
- For `suggest_outfit`: I'll give Claude the information from planning.md  and ask it to implement the LLM call using Groq's. I'll verify by calling it with `get_empty_wardrobe()` and confirming it returns a useful string instead of crashing, then calling it with `get_example_wardrobe()` and confirming the output references actual wardrobe items.
- For `create_fit_card`: I'll give Claude the tool 3 information from planning.md  and ask it to implement the LLM call with a temperature high enough to produce varied output. I'll verify by running it three times on the same input and confirming the captions differ, and by calling it with an empty outfit string and confirming it returns an error message string rather than raising an exception.

**Milestone 4 — Planning loop and state management:**

I'll use Claude and give everything from planning.md related to planning loops and state management.

I'll verify the output before running by checking: if it branches on `search_listings` returning an empty list, if it writes to `session["selected_item"]`, `session["outfit"]`, and `session["fit_card"]` at the correct moment, and if it ever calls `suggest_outfit` unconditionally without checking session first. Anything that doesn't match the spec I'll revise before running. I'll then test the no-results branch directly by passing an irrelevant query and confirming `session["fit_card"]` is `None` and `session["error"]` is set.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The agent calls `search_listings(description="vintage graphic tee", size=None, max_price=30.0)`.
No size was specified in the query, so that filter is skipped The tool scans the listings from listings.json and returns the top matches ranked by relevance. The output should look like the following "Faded Band Tee — $22, size M, Depop, Good Condition."
If no listings match, the agent tells the user what to adjust ("Nothing found — try a broader description or higher price limit") and stops. Steps 2 and 3 are not called.


**Step 2 (optional):**
Since the user didn't ask about price or value, `compare_price` is skipped. If the user had asked something like "is this a good deal?", the agent would call `compare_price(item=session["selected_item"])` here and store the verdict in `session["price_verdict"]` before continuing.



**Step 3:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
Fitfindr takes the top result from Step 1 and calls `suggest_outfit(new_item=<band tee>, wardrobe=<user's wardrobe>)`.
The wardrobe is populated from what the user described ("baggy jeans, chunky sneakers"). The tool returns a styled combination or suggestion for style like the following: "Pair the faded band tee with your wide-leg jeans and chunky sneakers. Tuck the front hem slightly and roll the sleeves once for a 90s silhouette." If the wardrobe is empty or too sparse to suggest anything, the agent asks the user for more wardrobe details before continuing to Step 3.

**Step 4:**
<!-- Continue until the full interaction is complete -->
Now fitfindr calls `create_fit_card(outfit=<suggestion from Step 2>, new_item=<band tee from Step 1>)`.
It generates a short, shareable caption: "thrifted this faded band tee for $22 and it was made for my wide-legs 🖤 rolled sleeves + slight front tuck = instant 90s"
If description generation fails, the agent falls back to a simple formatted summary of the outfit instead of a styled caption, so the user still gets a result.

**Final output to user:**
<!-- What does the user actually see at the end? -->
The matched listing (title, price, platform, condition), the outfit suggestion with styling notes, and the fit card caption ready to copy/share.

