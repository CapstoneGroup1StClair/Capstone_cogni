import yaml
import json
import os
from typing import Dict, Tuple
from dotenv import load_dotenv
from bson.json_util import ObjectId
from transformers import pipeline
from google.cloud import translate

load_dotenv()

DATABASE_URI = os.environ.get("MONGO_URI")
GCLOUD_PROJECT = os.environ.get("GCLOUD_PROJECT")

ObjectId = ObjectId

summarizer = pipeline("summarization", model="./bart-large-cnn/")

class MongoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(MongoEncoder, self).default(obj) 

mail_settings = {
    "MAIL_SERVER": os.environ['MAIL_SERVER'],
    "MAIL_PORT": 587,
    "MAIL_USE_TLS": True,
    "MAIL_USE_SSL": False,
    "MAIL_USERNAME": os.environ['MAIL_USERNAME'],
    "MAIL_PASSWORD": os.environ['MAIL_PASSWORD'],
    "MAIL_DEFAULT_SENDER": os.environ['MAIL_DEFAULT_SENDER'],
}

def get_summary(questionnaire, locale='en'):
    text = ''
    client = translate.TranslationServiceClient()
    for item in questionnaire:
        text += f'''Question: {item['question']}--Answer: {item['answer']}--'''
    if locale == 'fr':
        translated = client.translate_text(parent=GCLOUD_PROJECT, contents=[text], source_language_code='fr', target_language_code='en')
        text = translated.translations[0].translated_text
    text = "\n".join(text.split("--"))
    # compute min length
    max_length = 512
    min_length = 192
    print("len", len(text))
    if len(text) <= 450:
        min_length = 8
        max_length = 16
    elif len(text) <= 650:
        min_length = 16
        max_length = 32
    elif len(text) <= 850:
        min_length = 32
        max_length = 64
    elif len(text) <= 1000:
        min_length = 32
        max_length = 96
    elif len(text) <= 1250:
        min_length = 64
        max_length = 128
    elif len(text) <= 1500:
        min_length = 64
        max_length = 172
    elif len(text) <= 1800:
        min_length = 96
        max_length = 256
    elif len(text) <= 2000:
        min_length = 128
        max_length = 328
    elif len(text) <= 2400:
        min_length = 128
        max_length = 384
    summary = summarizer(text, max_length=max_length, min_length=min_length)
    summary_fr = ''
    try:
        if summary and len(summary):
            summary = summary[0].get('summary_text')
            summary_fr = client.translate_text(parent=GCLOUD_PROJECT,  contents=[summary], target_language_code='fr', source_language_code='en')
            summary_fr = summary_fr.translations[0].translated_text
    except:
        pass

    return summary, summary_fr

# Read answer config
with open('answers_conig.yaml') as f:
    answer_map = yaml.safe_load(f)

def get_score(question, answer):
    answer_conf_list = list(filter(lambda a: a['question_slug'] in question, answer_map))
    try:
        assert len(answer_conf_list) == 1
        assert answer not in ['', None]
    except:
        return 0
    answer_config = answer_conf_list[0]
    if answer_config['type'] == 'text':
        return 0
    if answer_config['type'] == 'single_select':
        try:
            return answer_config['answer_scores'][answer.strip()]
        except:
            return 0
    if answer_config['type'] == 'multi_select':
        total = 0
        ans = answer.split(";")
        for a in ans:
            try:
                total += answer_config['answer_scores'][a.strip()]
            except:
                pass
        return total

def process_answer(response: Dict) -> Tuple:
    severity_score = {
        'general': 0,
        'ptsd': 0,
        'anxiety': 0,
        'sud': 0,
        'trauma': 0
    }
    for q, a in response.items():
        if 'ptsd' in q:
            severity_score['ptsd'] += get_score(q, a)
        elif 'sud' in q:
            severity_score['sud'] += get_score(q, a)
        elif 'anxiety' in q:
            severity_score['anxiety'] += get_score(q, a)
        elif 'trauma' in q:
            severity_score['anxiety'] += get_score(q, a)
        else:
            severity_score['general'] += get_score(q, a)

    total_severity = sum(severity_score.values())

    return (total_severity, severity_score) 
