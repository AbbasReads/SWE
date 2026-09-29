# Students' Auditorium Management Software

Stack (as per the problem statement): Linux · MySQL (MariaDB) · Apache (mod_wsgi) · Python/Flask, run with Docker.

## Run

```
docker compose up --build       # http://localhost:8080   (Ctrl+C to stop)
docker compose down             # remove containers (data kept)
docker compose down -v          # also delete the database
```

Default logins: `manager/manager`, `sales1/sales1`, `clerk/clerk`.

## Tests

```
pip install -r requirements.txt
python -m unittest              # model tests (no DB needed)
```
