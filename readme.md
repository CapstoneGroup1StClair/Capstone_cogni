## Get Started

1. Clone the project on your computer and go to `server/` folder

2. Make copy of `.env` file from `.env.example` and add environment variables 

3. Update `google_translation_credentials.json` with key or create new key following [Setup Google Cloud Translation](https://cloud.google.com/translate/docs/setup)

4. Create MongoDB database with at-least one entry in `users` collection.
```
db.users.insertOne({ email: "admin@example.com", name: "Admin Email"})
```


#### Windows

5. `set GOOGLE_APPLICATION_CREDENTIALS="KEY_PATH"`

6. Create and activate a virtual environment  
```python
python -m venv .venv
.venv\Scripts\activate
```

7. Install dependencies  
```python
pip install -r requirements.txt
```

8. Run the server locally  
```python
python app.py
```

#### Linux/MacOS

5. `export GOOGLE_APPLICATION_CREDENTIALS="KEY_PATH"`

6. Create and activate a virtual environment
```python
python -m venv .venv
source .venv/bin/activate
```

7. Install dependencies
```python
pip install -r requirements.txt
```

8. Run the server
```python
python app.py
# or
export FLASK_APP=app.py
flask run --debug
```