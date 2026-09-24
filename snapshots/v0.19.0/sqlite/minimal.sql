-- base_checksum: 5f9fdc13f37784f35636839c48e11779672d49bfd4f64c61e24070fe4c595bc1
-- dbwarden: file-severity INFO
-- upgrade

CREATE TABLE IF NOT EXISTS users (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL
);

-- rollback

DROP TABLE users
