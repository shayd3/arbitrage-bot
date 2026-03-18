"""
Match ESPN game objects to Kalshi market tickers.
Uses static alias lookup for safety (no fuzzy matching on financial data).
"""
import re
from backend.models import Game, KalshiMarket, Sport

# Team name aliases → canonical abbreviation used in Kalshi tickers
# Format: "alias" -> "KALSHI_ABBREV"
TEAM_ALIASES: dict[str, str] = {
    # NBA
    "atlanta hawks": "ATL",
    "hawks": "ATL",
    "boston celtics": "BOS",
    "celtics": "BOS",
    "brooklyn nets": "BKN",
    "nets": "BKN",
    "charlotte hornets": "CHA",
    "hornets": "CHA",
    "chicago bulls": "CHI",
    "bulls": "CHI",
    "cleveland cavaliers": "CLE",
    "cavaliers": "CLE",
    "cavs": "CLE",
    "dallas mavericks": "DAL",
    "mavericks": "DAL",
    "mavs": "DAL",
    "denver nuggets": "DEN",
    "nuggets": "DEN",
    "detroit pistons": "DET",
    "pistons": "DET",
    "golden state warriors": "GSW",
    "warriors": "GSW",
    "houston rockets": "HOU",
    "rockets": "HOU",
    "indiana pacers": "IND",
    "pacers": "IND",
    "la clippers": "LAC",
    "los angeles clippers": "LAC",
    "clippers": "LAC",
    "la lakers": "LAL",
    "los angeles lakers": "LAL",
    "lakers": "LAL",
    "memphis grizzlies": "MEM",
    "grizzlies": "MEM",
    "miami heat": "MIA",
    "heat": "MIA",
    "milwaukee bucks": "MIL",
    "bucks": "MIL",
    "minnesota timberwolves": "MIN",
    "timberwolves": "MIN",
    "twolves": "MIN",
    "new orleans pelicans": "NOP",
    "pelicans": "NOP",
    "new york knicks": "NYK",
    "knicks": "NYK",
    "oklahoma city thunder": "OKC",
    "thunder": "OKC",
    "orlando magic": "ORL",
    "magic": "ORL",
    "philadelphia 76ers": "PHI",
    "76ers": "PHI",
    "sixers": "PHI",
    "phoenix suns": "PHX",
    "suns": "PHX",
    "portland trail blazers": "POR",
    "trail blazers": "POR",
    "blazers": "POR",
    "sacramento kings": "SAC",
    "kings": "SAC",
    "san antonio spurs": "SAS",
    "spurs": "SAS",
    "toronto raptors": "TOR",
    "raptors": "TOR",
    "utah jazz": "UTA",
    "jazz": "UTA",
    "washington wizards": "WAS",
    "wizards": "WAS",
}

SPORT_TICKER_PREFIX: dict[Sport, list[str]] = {
    Sport.NBA: ["KXNBAGAME", "KXNBA", "NBA"],
    Sport.NFL: ["KXNFLGAME", "KXNFL", "NFL"],
    Sport.MLB: ["KXMLBGAME", "KXMLB", "MLB"],
    Sport.NHL: ["KXNHLGAME", "KXNHL", "NHL"],
}

def normalize_team_name(name: str) -> str:
    """Normalize a team name to lowercase for alias lookup."""
    return name.lower().strip()

def team_to_kalshi_abbrev(team_name: str) -> str | None:
    """Look up Kalshi ticker abbreviation for a team name."""
    return TEAM_ALIASES.get(normalize_team_name(team_name))

def _ticker_contains_team(ticker: str, abbrev: str) -> bool:
    """Check if a Kalshi ticker contains a team abbreviation."""
    ticker_upper = ticker.upper()
    abbrev_upper = abbrev.upper()
    # Match patterns like -LAL-, _LAL_, LALNBA, etc.
    return bool(re.search(r'[-_]?' + re.escape(abbrev_upper) + r'[-_]?', ticker_upper))

def match_game_to_markets(game: Game, markets: list[KalshiMarket]) -> list[KalshiMarket]:
    """
    Find Kalshi markets that correspond to a given ESPN game.

    Handles the KXNBAGAME format where both teams are concatenated in the ticker:
      KXNBAGAME-26MAR17OKCORL-OKC  (away=OKC, home=ORL, outcome=OKC wins)
      KXNBAGAME-26MAR17OKCORL-ORL  (away=OKC, home=ORL, outcome=ORL wins)
    """
    home_abbrev = team_to_kalshi_abbrev(game.home_team.name)
    away_abbrev = team_to_kalshi_abbrev(game.away_team.name)

    home_abbrevs = {a.upper() for a in [home_abbrev, game.home_team.abbreviation] if a}
    away_abbrevs = {a.upper() for a in [away_abbrev, game.away_team.abbreviation] if a}

    sport_prefixes = SPORT_TICKER_PREFIX.get(game.sport, [])

    results = []
    for market in markets:
        if market.status not in OPEN_STATUSES:
            continue

        ticker = market.ticker.upper()

        if not any(ticker.startswith(pfx) for pfx in sport_prefixes):
            sport_str = game.sport.value.upper()
            if sport_str not in ticker:
                continue

        # Check for concatenated team pair (KXNBAGAME format): OKCORL or OKCORLANDO, etc.
        # Both teams must appear in the ticker (as a pair) to confirm it's this specific game.
        home_in_ticker = any(a in ticker for a in home_abbrevs)
        away_in_ticker = any(a in ticker for a in away_abbrevs)

        if home_in_ticker and away_in_ticker:
            results.append(market)

    return results

OPEN_STATUSES = {"open", "active"}

class GameMarketMatch:
    """Represents a matched game + market pair."""
    def __init__(self, game: Game, market: KalshiMarket, home_team_wins: bool):
        self.game = game
        self.market = market
        self.home_team_wins = home_team_wins  # Is YES = home team wins?

    @property
    def leading_team_yes_price(self) -> int | None:
        """YES price for the currently leading team."""
        home_leading = self.game.home_team.score > self.game.away_team.score
        if home_leading == self.home_team_wins:
            return self.market.yes_ask  # YES = leading team
        else:
            return self.market.no_ask   # Leading team is NO

    @property
    def lead(self) -> int:
        """Current score lead (positive = home winning)."""
        return abs(self.game.home_team.score - self.game.away_team.score)
