
Install backend locally:
```
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .\backend
python -m pip install -e .\backend[dev]
```

Run backend in Docker container:
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
and set your app informations, then update .env file with app credentials

to get inside postgres DB, after running docker compose go with
```
psql -u ${POSTGRES_USER} -d ${POSTGRES_DB}
```

to run frontend go with
```
sudo apt install npm
sudo npm install -g @angular/cli
cd frontend 
npm install
ng serve
```
