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

INSERT INTO patient
(patientennummer, alter, name, krankenkasse, krankheiten, `ehemalige aufenthalte`, `ehemalige medikamente`, bettnummer)
VALUES
(1001, 34, 'Mila Meier', 'CSS', 'Asthma', '2019: Bronchitis', 'Salbutamol', 12),
(1002, 58, 'Noah Keller', 'Helsana', 'Diabetes Typ 2', '2021: Knie-OP', 'Metformin', 14),
(1003, 22, 'Lea Schmid', 'SWICA', 'Migräne', '2020: Beobachtung', 'Ibuprofen', 15);

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

INSERT INTO arzt (ärztenummer, anstellzeit, name, spezialisierung)
VALUES
(501, 5, 'Dr. Anna Weber', 'Innere Medizin'),
(502, 12,'Dr. Tim Fischer','Neurologie');

CREATE TABLE aktuellerAufenthalt (
    bettnummer INTEGER PRIMARY KEY,
    pflegebedarf TEXT,
    anfangsdatum TEXT
);

INSERT INTO aktuellerAufenthalt (bettnummer, pflegebedarf, anfangsdatum)
VALUES
(12, 'mittel', '2026-01-10'),
(14, 'hoch',   '2026-01-12'),
(15, 'niedrig','2026-01-13');

CREATE TABLE nimmt (
    fachname TEXT PRIMARY KEY,
    patientennummer INTEGER PRIMARY KEY
);

CREATE TABLE behandelt (
    ärztenummer INTEGER PRIMARY KEY,
    patientennummer INTEGER PRIMARY KEY
);

INSERT INTO behandelt (ärztenummer, patientennummer)
VALUES
(501, 1001),
(501, 1002),
(502, 1003);

