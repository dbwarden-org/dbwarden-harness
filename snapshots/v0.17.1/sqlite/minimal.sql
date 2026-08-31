-- upgrade

CREATE TABLE IF NOT EXISTS users (
    id INTEGER NOT NULL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

-- rollback

DROP TABLE users
