from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import json
import os
from pymongo import MongoClient
from flask_mail import Mail, Message
from utils import MongoEncoder, DATABASE_URI, ObjectId
from utils import process_answer, mail_settings, get_summary
from datetime import datetime

print (DATABASE_URI)

client = MongoClient(DATABASE_URI)
db = client.capstone

app = Flask(__name__)
app.json_encoder = MongoEncoder
app.config.update(mail_settings)
mail = Mail(app)

@app.get('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                          'favicon.ico',mimetype='image/vnd.microsoft.icon')

#####   SurveyJS Routes   #############################
@app.get('/')
def index():
    questionnaires = list(db.questionnaire.find())
    return render_template('main.html', questionnaires=questionnaires)

@app.route('/view/<id>', methods=['GET', 'POST'])
def view(id):
    if id:
        doc = db.questionnaire.find_one({'_id': ObjectId(id)})
    if doc and doc.get('_id'):
        if request.method == 'POST':
            data = request.get_json()
            data['updated_at']= datetime.now()
            return {'success': True, 'id': id}
        title = ''
        try:
          title = doc['questionnaire']['title']['default']
        except:
            title = doc['questionnaire']['title'] or '' 
        return render_template('form.html', id=id, title=title, email=doc.get('email'), questionnaire=json.dumps(doc.get('questionnaire')))
    return render_template('form.html', questionnaire=json.dumps(doc.get('questionnaire')))

@app.route('/create-questionnaire', methods=['GET', 'POST'])
def create_questionnaire():
    if request.method == 'POST':
        data = request.get_json()
        data['updated_at']= datetime.now()
        id = db.questionnaire.insert_one(data).inserted_id
        return {'success': True, 'id': id}
    return render_template('surveycreator.html', id='', questionnaire={})

@app.route('/edit-questionnaire/<id>',  methods=['GET', 'POST'])
def edit_questionnaire(id):
    if id:
        doc = db.questionnaire.find_one({'_id': ObjectId(id)})
    if doc and doc.get('_id'):
        if request.method == 'POST':
            data = request.get_json()
            data['updated_at']= datetime.now()
            db.questionnaire.update_one({'_id': doc.get('_id')}, {'$set': data})
            return {'success': True, 'id': id}
        return render_template('surveycreator.html', id=id, email=doc.get('email'), questionnaire=json.dumps(doc.get('questionnaire')))
    return render_template('surveycreator.html', id='')

@app.route('/delete/<id>', methods=['GET'])
def delete_questionnaire(id):
    if id:
        doc = db.questionnaire.find_one({'_id': ObjectId(id)})
    if doc and doc.get('_id'):
        db.questionnaire.delete_one({'_id': doc.get('_id')})
    return redirect(url_for('index'))

##########    Summarization Route with BART on SurveyJS response    #############
@app.post('/submit')
def submit_response():
    data = request.get_json()
    data['created_at'] = datetime.utcnow()
    email_list = [user['email'] for user in db.users.find()]
    questionnaire_id = data.get('questionnaire')
    if questionnaire_id:
        qsn = db.questionnaire.find_one({'_id': ObjectId(questionnaire_id)})
        email_list = email_list + (qsn.get('email') or '').split(',')
    
    title = ''
    try:
        title = qsn['questionnaire']['title']['default']
    except:
        title = qsn['questionnaire']['title'] or ''

    data['questionnaire'] = qsn.get('_id')
    doc = db.responses.insert_one(data)
    response = data.get('response')
    summary, summary_fr = get_summary(response, data.get('locale'))
    if summary:
        summary = [line for line in summary.split('.') if len(line.strip()) > 0]
    if summary_fr and len(summary_fr) > 0:
        summary_fr = [line for line in summary_fr.split('.') if len(line.strip()) > 0]
    db.responses.update_one({'_id': doc.inserted_id}, {'$set': {'summary': summary}})
    db.responses.update_one({'_id': doc.inserted_id}, {'$set': {'summary_fr': summary_fr}})

    msg = Message('New Submission Receieved!', recipients=email_list)
    msg.body = render_template('cognisummary.html', summary=summary, summary_fr=summary_fr, title=title)
    msg.html = render_template('cognisummary.html', summary=summary, summary_fr=summary_fr, title=title)
    mail.send(msg)
    return {'success': True}

######################################################

###########    Play book Routes   #############################
@app.get('/playbook')
def playbook():
    all_questions = [{'name': question['name'], 'id': question['_id']} for question in db.questionnaire_playbook.find()]
    return render_template('questionnaire.html', all_questions=all_questions)

@app.get('/playbook/questionnaire/<id>')
def get_playbook_questionnaire(id):
    if id:
        doc = db.questionnaire_playbook.find_one({'_id': ObjectId(id)})
        if doc and doc.get('_id'):
            return {'success': True, 'data': doc}
    return {'success': False, 'data': None}

@app.post('/playbook/save-questionnaire')
def create_playbook_questionnaire():
    data = request.get_json()
    name = f"Sample {int(datetime.utcnow().timestamp())}"
    db.questionnaire_playbook.insert_one({
         'name': name,
         'questionnaire': data
    })
    return {'success': True}

##########    Summarization Route with BART    #############
@app.post('/summarize')
def compute_summary():
    data = request.get_json()
    email_list = [user['email'] for user in db.users.find()]
    email = data.get('email')
    if email:
        email_list = email_list + email.split(',')
    response = data.get('response')
    summary = get_summary(response)
    if summary:
        summary = [line for line in summary.split('.') if len(line.strip()) > 0]
    msg = Message('New Submission Receieved!', recipients=email_list)
    msg.body = render_template('cognisummary.html', summary=summary)
    msg.html = render_template('cognisummary.html', summary=summary)
    mail.send(msg)
    return {'success': True, 'data': summary}
######################################################

###########    Severity Calculation Route    #############
@app.post('/submit')
def get_form_submission():
    severity = 'GREEN'
    data = request.get_json()
    admin_emails = [user['email'] for user in db.users.find()]
    total_score, breakdown = process_answer(data)
    if total_score > 20:
        severity = 'RED'
    elif total_score > 12:
        severity = 'AMBER'
    data['severity'] = severity
    data['severity_breakdown'] = breakdown
    db.response.insert_one(data)
    msg = Message('Health and Wellness Survey: New Submission Receieved!', recipients=admin_emails)
    msg.body = render_template('cognixrsummary.html', **data)
    msg.html = render_template('cognixrsummary.html', **data)
    mail.send(msg)
    if data.get('provider_email') != None:
        msg.recipients = [data['provider_email']]
        mail.send(msg)
    return {'success': True, 'data': data}

######################################################

if __name__ == '__main__':
	app.run(debug=True)
