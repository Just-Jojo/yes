# A file containing... statements :kappa:

CREATE_PREFIX_TABLE: str = """CREATE TABLE IF NOT EXISTS
    guild_prefixes (
        guild_id INT PRIMARY KEY,
        prefixes TEXT NOT NULL
    )
""".strip()
SELECT_PREFIXES: str = """SELECT (guild_prefixes) FROM prefixes WHERE guild_id=:guild_id
""".strip()
INSERT_OR_UPDATE_PREFIXES = """INSERT OR REPLACE INTO
guild_prefixes
    (prefixes)
VALUES
    (:prefixes)
WHERE guild_id = :guild_id
""".strip()
