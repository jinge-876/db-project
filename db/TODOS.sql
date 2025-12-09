CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(250) NOT NULL UNIQUE,
    password VARCHAR(250) NOT NULL
);

CREATE TABLE todos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    content VARCHAR(100),
    due DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE patient (
    patientennummer INTEGER PRIMARY KEY,
    alter INTEGER,
    name TEXT,
    krankenkasse TEXT,
    krankheiten TEXT,
    ehemalige aufenthalte TEXT,
    ehemalige medikamente TEXT, 
    bettnummer INTEGER FOREIGN KEY
);

CREATE TABLE medizin (
    fachname TEXT PRIMARY KEY,
    dosierung TEXT
);


CREATE TABLE arzt (
    ärztenummer INTEGER PRIMARY KEY,
    anstellzeit INTEGER,
    name TEXT,
    spezialisierung TEXT
);

CREATE TABLE aktuellerAufenthalt (
    bettnummer INTEGER PRIMARY KEY,
    pflegebedarf TEXT,
    anfangsdatum TEXT
);

CREATE TABLE nimmt (
    fachname TEXT PRIMARY KEY,
    patientennummer INTEGER PRIMARY KEY
);

CREATE TABLE behandelt (
    ärztenummer INTEGER PRIMARY KEY,
    patientennummer INTEGER PRIMARY KEY
);



