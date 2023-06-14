import yaml
import json
import os
from typing import Dict, Tuple
from dotenv import load_dotenv
from bson.json_util import ObjectId
load_dotenv()

DATABASE_URI = os.environ.get("MONGO_URI")

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
            #print(f"{answer} not found for {question}")
            return 0
    if answer_config['type'] == 'multi_select':
        total = 0
        ans = answer.split(";")
        for a in ans:
            try:
                total += answer_config['answer_scores'][a.strip()]
            except:
                #print(f"{a} not found for {question}")
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
