"""
Match ESPN game objects to Kalshi market tickers.
Uses static alias lookup for safety (no fuzzy matching on financial data).
"""
import re
from datetime import timezone
from backend.models import Game, KalshiMarket, Sport

# Team name aliases → canonical abbreviation used in Kalshi tickers
# Scoped by sport to avoid cross-sport collisions (e.g. "kings" = SAC in NBA, LAK in NHL)
TEAM_ALIASES: dict[Sport, dict[str, str]] = {
    Sport.NBA: {
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
    },
    Sport.NFL: {
        "arizona cardinals": "ARI",
        "cardinals": "ARI",
        "atlanta falcons": "ATL",
        "falcons": "ATL",
        "baltimore ravens": "BAL",
        "ravens": "BAL",
        "buffalo bills": "BUF",
        "bills": "BUF",
        "carolina panthers": "CAR",
        "panthers": "CAR",
        "chicago bears": "CHI",
        "bears": "CHI",
        "cincinnati bengals": "CIN",
        "bengals": "CIN",
        "cleveland browns": "CLE",
        "browns": "CLE",
        "dallas cowboys": "DAL",
        "cowboys": "DAL",
        "denver broncos": "DEN",
        "broncos": "DEN",
        "detroit lions": "DET",
        "lions": "DET",
        "green bay packers": "GB",
        "packers": "GB",
        "houston texans": "HOU",
        "texans": "HOU",
        "indianapolis colts": "IND",
        "colts": "IND",
        "jacksonville jaguars": "JAX",
        "jaguars": "JAX",
        "kansas city chiefs": "KC",
        "chiefs": "KC",
        "las vegas raiders": "LV",
        "raiders": "LV",
        "los angeles chargers": "LAC",
        "chargers": "LAC",
        "los angeles rams": "LAR",
        "rams": "LAR",
        "miami dolphins": "MIA",
        "dolphins": "MIA",
        "minnesota vikings": "MIN",
        "vikings": "MIN",
        "new england patriots": "NE",
        "patriots": "NE",
        "pats": "NE",
        "new orleans saints": "NO",
        "saints": "NO",
        "new york giants": "NYG",
        "giants": "NYG",
        "new york jets": "NYJ",
        "jets": "NYJ",
        "philadelphia eagles": "PHI",
        "eagles": "PHI",
        "pittsburgh steelers": "PIT",
        "steelers": "PIT",
        "san francisco 49ers": "SF",
        "49ers": "SF",
        "niners": "SF",
        "seattle seahawks": "SEA",
        "seahawks": "SEA",
        "tampa bay buccaneers": "TB",
        "buccaneers": "TB",
        "bucs": "TB",
        "tennessee titans": "TEN",
        "titans": "TEN",
        "washington commanders": "WAS",
        "commanders": "WAS",
    },
    Sport.NHL: {
        "anaheim ducks": "ANA",
        "ducks": "ANA",
        "boston bruins": "BOS",
        "bruins": "BOS",
        "buffalo sabres": "BUF",
        "sabres": "BUF",
        "calgary flames": "CGY",
        "flames": "CGY",
        "carolina hurricanes": "CAR",
        "hurricanes": "CAR",
        "chicago blackhawks": "CHI",
        "blackhawks": "CHI",
        "colorado avalanche": "COL",
        "avalanche": "COL",
        "avs": "COL",
        "columbus blue jackets": "CBJ",
        "blue jackets": "CBJ",
        "dallas stars": "DAL",
        "stars": "DAL",
        "detroit red wings": "DET",
        "red wings": "DET",
        "edmonton oilers": "EDM",
        "oilers": "EDM",
        "florida panthers": "FLA",
        "panthers": "FLA",
        "los angeles kings": "LAK",
        "kings": "LAK",
        "minnesota wild": "MIN",
        "wild": "MIN",
        "montreal canadiens": "MTL",
        "canadiens": "MTL",
        "habs": "MTL",
        "nashville predators": "NSH",
        "predators": "NSH",
        "preds": "NSH",
        "new jersey devils": "NJD",
        "devils": "NJD",
        "new york islanders": "NYI",
        "islanders": "NYI",
        "new york rangers": "NYR",
        "rangers": "NYR",
        "ottawa senators": "OTT",
        "senators": "OTT",
        "sens": "OTT",
        "philadelphia flyers": "PHI",
        "flyers": "PHI",
        "pittsburgh penguins": "PIT",
        "penguins": "PIT",
        "pens": "PIT",
        "san jose sharks": "SJS",
        "sharks": "SJS",
        "seattle kraken": "SEA",
        "kraken": "SEA",
        "st. louis blues": "STL",
        "st louis blues": "STL",
        "blues": "STL",
        "tampa bay lightning": "TBL",
        "lightning": "TBL",
        "bolts": "TBL",
        "toronto maple leafs": "TOR",
        "maple leafs": "TOR",
        "leafs": "TOR",
        "utah hockey club": "UTA",
        "vancouver canucks": "VAN",
        "canucks": "VAN",
        "vegas golden knights": "VGK",
        "golden knights": "VGK",
        "washington capitals": "WSH",
        "capitals": "WSH",
        "caps": "WSH",
        "winnipeg jets": "WPG",
        "jets": "WPG",
    },
    Sport.MLB: {
        "arizona diamondbacks": "ARI",
        "diamondbacks": "ARI",
        "d-backs": "ARI",
        "atlanta braves": "ATL",
        "braves": "ATL",
        "baltimore orioles": "BAL",
        "orioles": "BAL",
        "o's": "BAL",
        "boston red sox": "BOS",
        "red sox": "BOS",
        "chicago cubs": "CHC",
        "cubs": "CHC",
        "chicago white sox": "CHW",
        "white sox": "CHW",
        "cincinnati reds": "CIN",
        "reds": "CIN",
        "cleveland guardians": "CLE",
        "guardians": "CLE",
        "colorado rockies": "COL",
        "rockies": "COL",
        "detroit tigers": "DET",
        "tigers": "DET",
        "houston astros": "HOU",
        "astros": "HOU",
        "kansas city royals": "KC",
        "royals": "KC",
        "los angeles angels": "LAA",
        "angels": "LAA",
        "los angeles dodgers": "LAD",
        "dodgers": "LAD",
        "miami marlins": "MIA",
        "marlins": "MIA",
        "milwaukee brewers": "MIL",
        "brewers": "MIL",
        "minnesota twins": "MIN",
        "twins": "MIN",
        "new york mets": "NYM",
        "mets": "NYM",
        "new york yankees": "NYY",
        "yankees": "NYY",
        "oakland athletics": "OAK",
        "athletics": "OAK",
        "a's": "OAK",
        "philadelphia phillies": "PHI",
        "phillies": "PHI",
        "pittsburgh pirates": "PIT",
        "pirates": "PIT",
        "san diego padres": "SD",
        "padres": "SD",
        "san francisco giants": "SF",
        "giants": "SF",
        "seattle mariners": "SEA",
        "mariners": "SEA",
        "st. louis cardinals": "STL",
        "st louis cardinals": "STL",
        "cardinals": "STL",
        "tampa bay rays": "TB",
        "rays": "TB",
        "texas rangers": "TEX",
        "rangers": "TEX",
        "toronto blue jays": "TOR",
        "blue jays": "TOR",
        "jays": "TOR",
        "washington nationals": "WSH",
        "nationals": "WSH",
        "nats": "WSH",
    },
    Sport.WNBA: {
        "atlanta dream": "ATL",
        "dream": "ATL",
        "chicago sky": "CHI",
        "sky": "CHI",
        "connecticut sun": "CONN",
        "sun": "CONN",
        "dallas wings": "DAL",
        "wings": "DAL",
        "golden state valkyries": "GSV",
        "valkyries": "GSV",
        "indiana fever": "IND",
        "fever": "IND",
        "las vegas aces": "LV",
        "aces": "LV",
        "los angeles sparks": "LA",
        "sparks": "LA",
        "minnesota lynx": "MIN",
        "lynx": "MIN",
        "new york liberty": "NY",
        "liberty": "NY",
        "phoenix mercury": "PHX",
        "mercury": "PHX",
        "seattle storm": "SEA",
        "storm": "SEA",
        "washington mystics": "WAS",
        "mystics": "WAS",
    },
}

SPORT_TICKER_PREFIX: dict[Sport, list[str]] = {
    Sport.NBA: ["KXNBAGAME", "KXNBA", "NBA"],
    Sport.NFL: ["KXNFLGAME", "KXNFL", "NFL"],
    Sport.MLB: ["KXMLBGAME", "KXMLB", "MLB"],
    Sport.NHL: ["KXNHLGAME", "KXNHL", "NHL"],
    Sport.WNBA: ["KXWNBAGAME", "KXWNBA", "WNBA"],
    Sport.CBB: ["KXCBBGAME", "KXCBB", "CBB"],
}

def normalize_team_name(name: str) -> str:
    """Normalize a team name to lowercase for alias lookup."""
    return name.lower().strip()

def team_to_kalshi_abbrev(team_name: str, sport: Sport) -> str | None:
    """Look up Kalshi ticker abbreviation for a team name within a sport."""
    sport_aliases = TEAM_ALIASES.get(sport, {})
    return sport_aliases.get(normalize_team_name(team_name))

def _ticker_contains_team(ticker: str, abbrev: str) -> bool:
    """Check if a Kalshi ticker contains a team abbreviation."""
    ticker_upper = ticker.upper()
    abbrev_upper = abbrev.upper()
    # Match patterns like -LAL-, _LAL_, LALNBA, etc.
    return bool(re.search(r'[-_]?' + re.escape(abbrev_upper) + r'[-_]?', ticker_upper))

# Max seconds between game start_time and market close_time to be considered
# the same game. Game winner markets close at tipoff, so this should be tight.
_GAME_TIME_TOLERANCE_SECS = 8 * 3600  # 8 hours

def match_game_to_markets(game: Game, markets: list[KalshiMarket]) -> list[KalshiMarket]:
    """
    Find Kalshi markets that correspond to a given ESPN game.

    Handles the KXNBAGAME format where both teams are concatenated in the ticker:
      KXNBAGAME-26MAR17OKCORL-OKC  (away=OKC, home=ORL, outcome=OKC wins)
      KXNBAGAME-26MAR17OKCORL-ORL  (away=OKC, home=ORL, outcome=ORL wins)
    """
    home_abbrev = team_to_kalshi_abbrev(game.home_team.name, game.sport)
    away_abbrev = team_to_kalshi_abbrev(game.away_team.name, game.sport)

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

        if not (home_in_ticker and away_in_ticker):
            continue

        # Guard against matching a future game's market to a currently in-progress game.
        # Game winner markets close at tipoff, so close_time should be within a few hours
        # of the game's start_time. If they're far apart, it's a different day's game.
        if game.start_time and market.close_time:
            game_start = game.start_time
            market_close = market.close_time
            # Normalise to UTC-aware for comparison
            if game_start.tzinfo is None:
                game_start = game_start.replace(tzinfo=timezone.utc)
            if market_close.tzinfo is None:
                market_close = market_close.replace(tzinfo=timezone.utc)
            diff = abs((market_close - game_start).total_seconds())
            if diff > _GAME_TIME_TOLERANCE_SECS:
                continue

        results.append(market)

    return results

OPEN_STATUSES = {"open", "active"}


def sport_from_ticker(ticker: str) -> Sport | None:
    """Determine the Sport from a Kalshi ticker prefix."""
    ticker_upper = ticker.upper()
    for sport, prefixes in SPORT_TICKER_PREFIX.items():
        if any(ticker_upper.startswith(pfx) for pfx in prefixes):
            return sport
    return None


def match_markets_to_games(
    markets: list[KalshiMarket], games: list[Game]
) -> list[tuple[Game, KalshiMarket]]:
    """Iterate markets and find the matching game for each.

    Returns a list of (game, market) pairs. Reuses match_game_to_markets
    internally so matching logic stays in one place.
    """
    games_by_sport: dict[Sport, list[Game]] = {}
    for g in games:
        games_by_sport.setdefault(g.sport, []).append(g)

    pairs: list[tuple[Game, KalshiMarket]] = []
    for market in markets:
        sport = sport_from_ticker(market.ticker)
        if not sport:
            continue
        for game in games_by_sport.get(sport, []):
            if match_game_to_markets(game, [market]):
                pairs.append((game, market))
                break
    return pairs


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
