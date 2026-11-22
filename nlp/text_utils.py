"""
nlp/text_utils.py

Small text helpers shared by the extractors. Three jobs:

    1. clean_option_phrase()  "sqlite since it's simple"  ->  "sqlite"
    2. same_option()          "postgres" vs "PostgreSQL"   ->  True
    3. display_name()         "redis session based auth"  ->  "Redis Session Based Auth"

How option matching works (same_option / match_score)
-----------------------------------------------------
Each phrase becomes a set of normalized tokens ("Redis-backed sessions" ->
{redis, backed, session}). Aliases map common nicknames to one spelling
(postgres -> postgresql, mongo -> mongodb). Then:

    score = weight(shared tokens) / weight(smaller phrase)

Generic words like "auth", "based" or "database" only count 0.25, so
"JWT auth" and "session based auth" do NOT match just because both say "auth",
while "session based auth" DOES match "redis session based auth" (score 1.0).
Two phrases name the same option when score >= 0.6.
"""

import re


# --- Normalization -----------------------------------------------------------

ALIASES = {
    "postgres": "postgresql",
    "pg": "postgresql",
    "psql": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "js": "javascript",
    "ts": "typescript",
    "mtls": "tls",
    "authentication": "auth",
    "authorization": "auth",
    "db": "database",
}

# Words that carry little meaning on their own when comparing options.
GENERIC_WORDS = {
    "auth", "based", "database", "approach", "solution", "option", "server",
    "side", "system", "service", "library", "framework", "store", "storage",
    "stack", "tool", "method", "strategy", "mutual", "backed", "layer", "engine",
}
GENERIC_WEIGHT = 0.25

STOP_WORDS = {
    "a", "an", "the", "of", "in", "on", "for", "to", "with", "and", "or", "our",
    "my", "your", "its", "it", "this", "that", "these", "those", "we", "i", "you",
    "is", "are", "be", "use", "using", "via", "through", "some", "any",
}

MATCH_THRESHOLD = 0.6


def tokens(text: str) -> set[str]:
    """Lowercase, split on non-word characters, apply aliases, drop stop words."""
    result: set[str] = set()
    for raw in re.split(r"[^a-z0-9+#]+", text.lower()):
        if not raw or raw in STOP_WORDS:
            continue
        word = ALIASES.get(raw, raw)
        # Very light plural handling: "sessions" -> "session", "tokens" -> "token".
        if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "is", "us", "os")):
            word = ALIASES.get(word[:-1], word[:-1])
        result.add(word)
    return result


def _weight(words: set[str]) -> float:
    return sum(GENERIC_WEIGHT if w in GENERIC_WORDS else 1.0 for w in words)


def match_score(a: str, b: str) -> float:
    """How strongly two phrases refer to the same option (0.0 - 1.0)."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    shared = ta & tb
    if not (shared - GENERIC_WORDS):
        # Sharing only generic words ("auth") never counts as a match.
        return 0.0
    return _weight(shared) / min(_weight(ta), _weight(tb))


def same_option(a: str, b: str) -> bool:
    return match_score(a, b) >= MATCH_THRESHOLD


def best_match(phrase: str, options: list[str]) -> str | None:
    """Return the option that best matches `phrase`, or None if none matches."""
    scored = [(match_score(phrase, option), option) for option in options]
    scored = [pair for pair in scored if pair[0] >= MATCH_THRESHOLD]
    if not scored:
        return None
    return max(scored, key=lambda pair: pair[0])[1]


def mentions(sentence_text: str, option: str) -> bool:
    """Does a sentence mention an option? (all non-generic option tokens present)"""
    option_tokens = tokens(option) - GENERIC_WORDS or tokens(option)
    return bool(option_tokens) and option_tokens <= tokens(sentence_text)


# --- Cleaning captured phrases -----------------------------------------------

# A captured option phrase ends where any of these begins:
#   "sqlite since it's simple"          -> "sqlite"
#   "JWT access tokens with a short expiry" -> "JWT access tokens"
PHRASE_END = re.compile(
    r"\s*(?:[,;:()]|\s[-–—]\s|\.\.\.|\.(?:\s|$)|!|\?|"
    r"\b(?:because|since|as|so|due to|given|in order to|to|instead of|rather than|"
    r"over|for|with|here|now|then|which|that|who|is|are|was|were|seems?|would|will|"
    r"should|could|can|if|but|when|while|and then|in our|in the|in this|from now)\b).*$",
    re.IGNORECASE,
)
LEADING_FILLER = re.compile(
    r"^(?:(?:ok(?:ay)?|so|then|yeah|yes|well|honestly|fair|fine|hmm+|alright|also|"
    r"i think|i guess|i feel like|maybe|perhaps|probably|just|the|a|an|our|my|some|"
    r"using|use)\b[\s,!.]*)+",
    re.IGNORECASE,
)
TRAILING_FILLER = re.compile(
    r"(?:\s+\b(?:here|now|then|instead|please|too|also|approach|one|option|again)\b)+$",
    re.IGNORECASE,
)

# Phrases that are about the discussion itself, never a real option.
JUNK_OPTION_WORDS = {
    "option", "options", "alternative", "alternatives", "choice", "choices",
    "approaches", "several", "few", "things", "stuff", "something", "anything",
    "files", "it", "this", "that", "them", "both", "either", "neither", "one",
}

MAX_OPTION_WORDS = 6


def clean_option_phrase(phrase: str, *, from_end: bool = False) -> str | None:
    """
    Trim a raw regex capture down to just the option name.

    from_end=False: the option starts the phrase ("sqlite since ...")  -> cut the tail.
    from_end=True:  the option ends the phrase ("For orders..., PostgreSQL") -> keep
                    only what follows the last comma / colon.
    Returns None if nothing meaningful is left.
    """
    phrase = phrase.strip().strip("\"'")
    if from_end:
        phrase = re.split(r"[,;:]", phrase)[-1]
    else:
        phrase = PHRASE_END.sub("", phrase)

    phrase = LEADING_FILLER.sub("", phrase.strip())
    phrase = TRAILING_FILLER.sub("", phrase)
    phrase = phrase.strip(" .,!?;:\"'")

    words = phrase.split()
    if not words or len(words) > MAX_OPTION_WORDS:
        return None
    if {w.lower() for w in words} & JUNK_OPTION_WORDS:
        return None
    if not tokens(phrase):
        return None
    return phrase


# --- Display names -----------------------------------------------------------

KNOWN_NAMES = {
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "mysql": "MySQL",
    "sqlite": "SQLite", "mongodb": "MongoDB", "mongo": "MongoDB", "redis": "Redis",
    "jwt": "JWT", "tls": "TLS", "mtls": "mTLS", "api": "API", "rest": "REST",
    "graphql": "GraphQL", "grpc": "gRPC", "oauth": "OAuth", "oauth2": "OAuth2",
    "sql": "SQL", "nosql": "NoSQL", "orm": "ORM", "aws": "AWS", "gcp": "GCP",
    "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "kafka": "Kafka", "rabbitmq": "RabbitMQ", "nginx": "Nginx", "react": "React",
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "sqlalchemy": "SQLAlchemy", "ci": "CI", "cd": "CD", "acid": "ACID",
    "jsonb": "JSONB", "http": "HTTP", "https": "HTTPS", "cors": "CORS",
    "rbac": "RBAC", "sso": "SSO", "ui": "UI", "s3": "S3", "zxing": "ZXing",
    "typescript": "TypeScript", "javascript": "JavaScript", "python": "Python",
    "express": "Express", "vite": "Vite", "celery": "Celery", "id": "ID",
}
SMALL_WORDS = {"a", "an", "the", "of", "in", "on", "for", "to", "with", "and", "or", "via"}


def display_name(phrase: str) -> str:
    """Title-case a phrase while keeping known product spellings (SQLite, JWT...)."""
    words = []
    for index, word in enumerate(phrase.split()):
        parts = [_display_word(part) for part in word.split("-")]
        shown = "-".join(parts)
        if index > 0 and word.lower() in SMALL_WORDS:
            shown = word.lower()
        words.append(shown)
    return " ".join(words)


def _display_word(word: str) -> str:
    if word.lower() in KNOWN_NAMES:
        return KNOWN_NAMES[word.lower()]
    if any(ch.isupper() for ch in word):
        return word  # The user already chose a casing ("ZXing", "iOS"): keep it.
    return word[:1].upper() + word[1:]
