# A file containing... statements :kappa:

CREATE_PREFIX_TABLE: str = """CREATE TABLE IF NOT EXISTS
    guild_prefixes (
        guild_id INT PRIMARY KEY,
        prefixes TEXT NOT NULL
    )
""".strip()
SELECT_PREFIXES: str = """SELECT (prefixes) FROM guild_prefixes WHERE guild_id=:guild_id
""".strip()
UPSERT_PREFIXES: str = """INSERT OR REPLACE INTO
guild_prefixes
    (guild_id, prefixes)
VALUES
    (:guild_id, :prefixes)
""".strip()

# Blacklist stuffs
CREATE_BLACKLIST_TABLE: str = """CREATE TABLE IF NOT EXISTS
    blacklist (
        user_id INT PRIMARY KEY,
        reason TEXT NOT NULL
    )
""".strip()

SELECT_BLACKLIST: str = """SELECT (reason) FROM blacklist WHERE user_id=:user_id"""

UPSERT_REASON: str = """INSERT OR REPLACE INTO
blacklist
    (user_id, reason)
VALUES
    (:user_id, :reason)
""".strip()
