from flask import Flask, render_template, request
from pymongo import MongoClient
from flask_mail import Mail, Message
from utils import MongoEncoder, DATABASE_URI, mail_settings
from utils import process_answer

client = MongoClient(DATABASE_URI)
db = client.capstone

app = Flask(__name__)
app.json_encoder = MongoEncoder
app.config.update(mail_settings)
mail = Mail(app)

@app.get('/')
def index():
    sample_record = db.response.find_one({}, sort=[( '_id', -1 )])
    # admin_emails = [user['email'] for user in db.users.find()]
    # msg = Message('Health and Wellness Survey: New Submission Receieved!', recipients=admin_emails)
    # msg.body = render_template('cognixrsummary.html', **sample_record)
    # msg.html = render_template('cognixrsummary.html', **sample_record)
    # mail.send(msg)
    return render_template('cognixrsummary.html', **sample_record)

@app.post('/')
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

if __name__ == '__main__':
	app.run(debug=True)
