
Install backend locally:
```
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .\backend
python -m pip install -e .\backend[dev]
```

Run backend in Docker container:
```
docker compose build
docker compose up -d
```
