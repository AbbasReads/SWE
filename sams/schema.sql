-- Students' Auditorium Management Software: MySQL schema (InnoDB for transactions / row locks)

CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    password        VARCHAR(255) NOT NULL,
    name            VARCHAR(100) NOT NULL,
    role            ENUM('manager', 'sales', 'clerk') NOT NULL,
    commission_rate DECIMAL(5, 4) NOT NULL DEFAULT 0
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS shows (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    title          VARCHAR(200) NOT NULL,
    date           DATE NOT NULL,
    timing         TIME NOT NULL,
    balcony_price  DECIMAL(10, 2) NOT NULL,
    ordinary_price DECIMAL(10, 2) NOT NULL,
    balcony_seats  INT NOT NULL,
    ordinary_seats INT NOT NULL,
    comp_balcony   INT NOT NULL DEFAULT 0,
    comp_ordinary  INT NOT NULL DEFAULT 0,
    UNIQUE (date, timing)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS tickets (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    show_id        INT NOT NULL,
    category       ENUM('balcony', 'ordinary') NOT NULL,
    seat_no        VARCHAR(10) NOT NULL,
    price          DECIMAL(10, 2) NOT NULL,
    booking_date   DATE NOT NULL,
    salesperson_id INT NOT NULL,
    status         ENUM('BOOKED', 'CANCELLED') NOT NULL DEFAULT 'BOOKED',
    refund         DECIMAL(10, 2) NOT NULL DEFAULT 0,
    FOREIGN KEY (show_id) REFERENCES shows (id),
    FOREIGN KEY (salesperson_id) REFERENCES users (id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS expenditures (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    show_id     INT NOT NULL,
    type        VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    amount      DECIMAL(10, 2) NOT NULL,
    date        DATE NOT NULL,
    FOREIGN KEY (show_id) REFERENCES shows (id)
) ENGINE = InnoDB;
