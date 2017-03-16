''' =========================================================================================== '''
# ChatIO RESTful App with SocketIO for Real-Time Chatting

''' =========================================================================================== '''
# Third-party Imports
from flask import render_template
from flask import request
from flask import abort
from flask import redirect, url_for
from flask import session
from flask import jsonify
from flask import make_response, request, current_app, g
from flask_socketio import SocketIO, send, emit, disconnect
from datetime import datetime
from datetime import timedelta
from functools import update_wrapper
from sqlalchemy import *
from sqlalchemy.sql import func
from passlib.hash import sha256_crypt
import boto3
import requests
import json

# Local Imports
from app import create_app
from app import models
from app.models import *
from app import db
from env import *


''' =========================================================================================== '''
# Instantiate the app
app = create_app(FLASK_CONFIG)

# Socket-IO Config
socketio = SocketIO(app)

# Function that tricks AWS S3 CORS into allowing all localhost origin
def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

''' =========================================================================================== '''
# ChatIO Routes

'''
Description: Render the login view here from templates
Input: None
Return Type: HTML, a view generated by render_template()
'''
@app.route('/', methods=['GET', 'POST'])
def login_view():
    if request.method == 'POST':
        session.pop('theUser', None)
        user = User.query.filter_by(username=request.form['username']).first()
        if user is not None:
            if sha256_crypt.verify(request.form['password'], user.password):
                session['theUser'] = request.form['username']
                return redirect(url_for('chat_view'))
    return render_template('/home/login.html')

'''
Description: Checks if user is in session before any request, if they are then set g.user
Input: None
Return Type: None
'''
@app.before_request
def before_request():
    g.user = None
    if 'theUser' in session:
        g.user = session['theUser']

'''
Description: Checks if user is in session before any request, if they are then set g.user
Input: None
Return Type: If user in session, then returns their name, if not then returns that your not logged
             in. Used to test if flask-session was working correctly
'''
@app.route('/getsession')
def getsession():
    if 'theUser' in session:
        return session['theUser']

    return 'Not logged in!'

'''
Description: Pops user from the session, logging them out
Input: None
Return Type: Redirects user to login page
'''
@app.route('/logout')
def dropsession():
    session.pop('theUser', None)
    return redirect(url_for('login_view'))

'''
Description: Render the main chat view here from templates, if a user is logged in
Input: None
Return Type: HTML, a view generated by render_template()
'''
@app.route('/chat')
def chat_view():
    if g.user:
        users = models.User.query.all()
        query = db.session.query(Message, User).filter(Message.sender_id==User.id)
        return render_template('/home/index.html', currUser=g.user, users=users, query=query)
    return redirect(url_for('login_view'))

'''
Description: Renders the API view from template, if a user is logged in
Input: None
Return Type: HTML, a view generated by render_template()
'''
@app.route('/api')
def api_view():
    if g.user:
        loginURL = 'http://smartplug.host/api/v1/auth/login'
        loginData = {'email': SMARTPLUG_API_EMAIL, 'password': SMARTPLUG_API_PASSWORD}
        tokenResponse = requests.post(loginURL, data=loginData)
        token = tokenResponse.json().get('token')

        lightURL = 'http://smartplug.host/api/v1/devices/%s/light' % SMARTPLUG_MAC
        headers = {'Token-Authorization': token}
        lightResponse = requests.get(lightURL, headers = headers)
        lightData = lightResponse.json()

        return render_template('/home/api.html', lightData=lightData, currUser=g.user)
    return redirect(url_for('login_view'))

'''
Description: Render the user profile here from templates
Input: user_id
Return Type: HTML, a view generated by render_template()
'''
@app.route('/user/<string:username>')
def user_profile(username):
    if g.user:
        user = User.query.filter_by(username=username).first()
        return render_template('/home/userprofile.html', user=user)
    return redirect(url_for('login_view'))

'''
Description: Retrieve a collection of users from the database, if the user is logged in
Input: None
Return Type: JSON, a JSON object containing the list of users
'''
@app.route('/users')
def getUsers():
    if g.user:
        usersList = User.query.all()
        return jsonify(User.serialize_list(usersList))
    return redirect(url_for('login_view'))

'''
Description: API method that allows logged in users to post message via API call at this route
Input: None
Return Type: JSON, a JSON object containing the message that was POST'ed
'''
@app.route('/message', methods=['POST'])
def postMessage():
    if g.user:
        if not request.json or not 'username' in request.json or not 'messageText' in request.json:
            abort(400)
        messageData = request.json
        username = messageData['username']
        messageText = messageData['messageText']
        timeStamp = datetime.now()

        sender = User.query.filter_by(username=username).first()
        if sender is not None:
            message = Message(messageTxt=messageText, dateTime=timeStamp, sender_id=sender.id)

        msg = {}
        msg['timeStamp'] = timeStamp.strftime('%Y-%m-%d %H:%M:%S')
        msg['user'] = username
        msg['txt'] = messageText
        db.session.add(message)
        db.session.commit()
        socketio.emit('json_msg_response', msg, broadcast=True)
        return json.dumps(request.json)
    return redirect(url_for('login_view'))

'''
Description: Retrieve a collection of messages from the database
Input: None
Return Type: JSON, a JSON object containing the list of messages
'''
@app.route('/messages')
def flutter():
    if g.user:
        messageList = Message.query.all()
        return jsonify(Message.serialize_list(messageList))
    return redirect(url_for('login_view'))


'''
Description: Returns presigned POST url for AWS S3 Bucket upload
Input: URL Arguments for filename and filetype
Return Type: Presigned AWS S3 POST URL
'''
@app.route('/sign_s3/', methods=['GET','POST','OPTIONS'])
@crossdomain(origin='*')
def sign_s3():

    file_name = request.args.get('file_name')
    file_type = request.args.get('file_type')

    s3 = boto3.client('s3')

    presigned_post = s3.generate_presigned_post(
        Bucket = S3_BUCKET,
        Key = file_name,
        Fields = {"acl": "public-read", "Content-Type": file_type},
        Conditions = [
            {"acl": "public-read"},
            {"Content-Type": file_type}
        ],
        ExpiresIn = 3600
    )

    return json.dumps({
        'data': presigned_post,
        'url': 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, file_name)
    })

'''
Description: Returns presigned POST url for AWS S3 Bucket upload
Input: URL Arguments for username and S3 image path to their uploaded image
Return Type: JSON showing username and image path for uploaded URL (not needed)
             by client side, but works this way.
'''
@app.route('/update_img/', methods=['GET','POST','OPTIONS'])
def updateProfileImg():
    theUser = request.args.get('user')
    theImgPath = request.args.get('imgPath')
    print theUser
    print theImgPath

    user = User.query.filter_by(username=theUser).first()
    user.pic_path = theImgPath
    db.session.commit()

    return json.dumps({
        'user': theUser,
        'url': theImgPath
    })

'''
Description: SocketIO method that handles messages sent by a user
Input: None
Return Type: None, emits the message sent by a user to the channel 'json_msg_response'
'''
@socketio.on('json_msg')
def handleMessage(msg):
    receiveMessageDateTime = datetime.now()
    msg['timeStamp'] = receiveMessageDateTime.strftime("%Y-%m-%d %H:%M:%S")
    sender = User.query.filter_by(username=msg['user']).first()
    message = Message(messageTxt=msg['txt'], dateTime=receiveMessageDateTime, sender_id=sender.id)
    db.session.add(message)
    db.session.commit()
    emit('json_msg_response', msg, broadcast=True)

'''
Description: SocketIO method that disconnects a user from SocketIO server connection
Input: None
Return Type: Prints statement on server side that user logged out
'''
@socketio.on('disconnect')
def socketio_disconnect():
    print 'A user has disconnected'

''' =========================================================================================== '''
# run the app
if __name__ == '__main__':
    socketio.run(app)
