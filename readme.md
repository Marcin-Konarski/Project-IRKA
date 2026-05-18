
Install backend locally:
```
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .\backend
python -m pip install -e .\backend[dev]
```

You need to set up your .env file 

Run whole application in Docker container:
```
docker compose up -d --build
```

Set you Telegram credentials beforehand
```
https://my.telegram.org/auth
```
then get to
```
https://my.telegram.org/apps
```
and set your app informations

# IMPORTANT
Remember to validate your telegram access on /telegram endpoint, you need to input special code which will be sent to the your telephone number.

to get inside postgres DB, after running docker compose go with
```
docker compose exec -it postgres bash
psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}
```

