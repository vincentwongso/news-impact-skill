# Symbol aliases

The pre-filter decides which watchlist symbols a headline *might* affect before any LLM
cost. It does this with an alias map keyed by currency/asset code.

For each watchlist symbol, the filter collects:
- the symbol string itself (e.g. `EURUSD`), and
- for every alias-key code that is a substring of the symbol, that code plus its terms.

So `EURUSD` pulls in the `EUR` terms (`Lagarde, ECB, euro, eurozone`) **and** the `USD`
terms (`Powell, Fed, FOMC, CPI, NFP`). `XAUUSD` pulls in `XAU` (`gold, bullion`) and `USD`.

Matching is case-insensitive and word-boundary aware, so `Fed` does not match `FedEx`.
A headline that hits zero symbols is dropped before the model is called.

Extend the map in `config.yaml` under `aliases:`. Keys are codes; values are term lists.
