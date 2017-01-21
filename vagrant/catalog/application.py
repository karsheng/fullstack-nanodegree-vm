from flask import Flask, render_template, url_for, request
from flask import redirect, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
from functools import wraps

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

app = Flask(__name__)

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create a login decorator function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated_function

# Main page displaying catalog with latest added items


@app.route('/')
@app.route('/catalog')
def main():
    categories = session.query(Category).all()
    items = session.query(Item).order_by(Item.id.desc()).limit(10)
    if 'username' not in login_session:
        return render_template('publicmain.html',
                               categories=categories, items=items)
    return render_template('main.html', categories=categories,
                           items=items, username=login_session['username'])

# Display all items of a particular category


@app.route('/catalog/<string:category_name>/items')
def showItemList(category_name):
    categories = session.query(Category).all()
    category_items = session.query(Item).join(
        Item.category).filter(Category.name == category_name)
    if 'username' not in login_session:
        return render_template('publicitems.html',
                               categories=categories,
                               category_name=category_name,
                               category_items=category_items)
    return render_template('items.html', categories=categories,
                           category_name=category_name,
                           category_items=category_items,
                           username=login_session['username'])

# Display item details


@app.route('/catalog/<string:category_name>/<string:item_name>')
def showItemDetails(category_name, item_name):
    item = session.query(Item).join(Item.category).filter(
        Category.name == category_name).filter(Item.name == item_name).one()
    creator = getUserInfo(item.user_id)

    # Display public version (without edit and delete function) if user is not
    # logged in or not the creator of the item
    if 'username' not in login_session:
        return render_template('publicitem.html', item=item)

    if creator.id != login_session['user_id']:
        return render_template('publicitem.html', item=item)

    return render_template('item.html',
                           item=item,
                           username=login_session['username'])

# Adds item to a specific category


@app.route('/catalog/add', methods=['GET', 'POST'])
@login_required
def addItem():
    if request.method == 'POST':
        if (not request.form['name'] or
                not request.form['description'] or
                not request.form['category']):
            flash("Please ensure all fields are filled!")
            return render_template(
                'newItem.html',
                username=login_session['username']), 400
        item_name = request.form['name']
        itemInDb = session.query(Item).filter_by(name=item_name)
        if itemInDb.count():
            flash("Item already exist!")
            return render_template(
                'newItem.html',
                username=login_session['username']), 400
        category_name = request.form['category']
        category_id = session.query(Category).filter_by(
            name=category_name).one().id
        newItem = Item(name=request.form['name'],
                       description=request.form['description'],
                       category_id=category_id,
                       user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash('New Item Created!')
        return redirect(url_for('showItemList', category_name=category_name))
    else:
        return render_template('newItem.html',
                               username=login_session['username'])

# Edits an item


@app.route('/catalog/<string:item_name>/edit', methods=['GET', 'POST'])
@login_required
def editItem(item_name):
    editedItem = session.query(Item).filter_by(name=item_name).one()
    # Forbids non-creator of the item from editting the item
    if editedItem.user_id != login_session['user_id']:
        return render_template('forbidden.html'), 403

    if request.method == 'POST':
        if (not request.form['name'] or
                not request.form['description'] or
                not request.form['category']):
            flash("Please ensure all fields are filled!")
            return render_template('editItem.html',
                                   item=editedItem,
                                   username=login_session['username']), 400
        editedItem.name = request.form['name']
        editedItem.description = request.form['description']
        category = session.query(Category).filter_by(
            name=request.form['category']).one()
        category_id = category.id
        category_name = category.name
        editedItem.category_id = category_id
        session.add(editedItem)
        session.commit()
        flash('Item Edited!')
        return redirect(url_for('showItemDetails',
                                category_name=category_name,
                                item_name=editedItem.name))
    else:
        return render_template('editItem.html',
                               item=editedItem,
                               username=login_session['username'])

# Deletes an item


@app.route('/catalog/<string:item_name>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteItem(item_name):
    deletedItem = session.query(Item).filter_by(name=item_name).one()

    # Forbids non-creator of the item from deleting the item
    if deletedItem.user_id != login_session['user_id']:
        return render_template('forbidden.html'), 403

    if request.method == 'POST':
        category_name = deletedItem.category.name
        session.delete(deletedItem)
        session.commit()
        flash('Item Deleted!')
        return redirect(url_for('showItemList', category_name=category_name))
    else:
        return render_template(
            'deleteitem.html',
            item=deletedItem,
            username=login_session['username'])

# Returns the full catalog in JSON


@app.route('/catalog/<string:category_name>/<string:item_name>/json')
def catalogJSON(category_name, item_name):
    item = session.query(Item).join(Item.category).filter(
        Category.name == category_name).filter(Item.name == item_name).one()
    return jsonify(item=item.serialize)

# Create anti-forgery state token


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

# Connect / login with Google+


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1].decode("utf8"))
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    output += '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# Disconnect / logout with Google+


def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        return "you have been logged out"

# Connect/log in with Facebook


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=\
    fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly
    # logout, let's strip out the information before the equals sign in our
    # token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=\
    200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;'
    output += 'border-radius: 150px;-webkit-border-radius: 150px;'
    output += '-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output

# Disconnect / logout with Facebook


def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
        facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"

# Disconnect based on provider


@app.route('/disconnect')
@app.route('/logout')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('main'))
    else:
        flash("You were not logged in")
        return redirect(url_for('main'))


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def getUserInfo(user_id):
    try:
        user = session.query(User).filter_by(id=user_id).one()
        return user
    except:
        return None


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


if __name__ == '__main__':
    app.secret_key = '458GEF39VHQB9009BQHQW8HC3871CE8GEFVQHC'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
