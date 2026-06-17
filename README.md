# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

## Tool Inputs

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

## How the planning loop works

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

## State management approach

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

## Error handling strategy

## Error Handling
| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets `session["error"]`, tells the user nothing matched and suggests adjustments (broaden description, raise price limit, remove size filter), returns early without calling further tools |
| compare_price | Fewer than 2 comparable listings found | Skips the verdict, notes in session that price data was unavailable, and continues to `suggest_outfit` — user is informed in the final output |
| suggest_outfit | Wardrobe is empty | Pauses the loop, asks the user to describe a few pieces they own, updates the wardrobe with their response, then retries the tool |
| create_fit_card | Outfit input is missing or incomplete | Falls back to generating a minimal caption using only the `title`, `price`, and `platform` fields from `session["selected_item"]` |

**Concrete Example**
The output from "designer ballgown size XXS under $5" is "No listings matched your search. Try broadening your description, raising your price limit, or removing the size filter."

The handling of that case is shown below:

[STEP 2] Parsed query:
  description : designer ballgown
  size        : XXS
  max_price   : 5.0

[STEP 3] Calling search_listings('designer ballgown', size=XXS, max_price=5.0)
  → 0 result(s) found
  ✗ No results — stopping early. Error set in session.
  session['fit_card'] = None (tools after search were NOT called)

The code immediately stops after the search step since nothing sufficient was found.

## Spec reflection
Overall the spec was great for getting my thoughts organized and having great context to feed claude when it generated my scripts. I revised my spec when I caught issues so my final code doesn't greatly deviate from it. One example of a minor deviation in my prompting to AI is that the user no longer has to ask if a listing is a good deal for compare_price() to run, it will always run to give the user its verdict because it made implementation a lot simpler and the app more user friendly as they no longer have to think about remembering to prompt about price.

## AI usage section

The first instance I used AI and had to revise it was when creating the compare_price(). I asked it to write the tool as the spec had it and did not remember to add it in the UI. When I did override the original result to include it in the UI, it still didn't show anything related to the price unless I prompted it using specific wording. I ended up changing it as I believe this made the final product more user friendly.

The second instance I used AI was in the run_agent(). Initially, I just had it running between tools and giving the final result. However, for the video I had to show it jumping from tool to tool so I asked Claude to re-do that part with explanations of each step and what tool was being called for clarity.
