from flask import Blueprint, render_template, url_for,request, redirect, session

# Assuming you are using Blueprints based on your file structure
home_bp = Blueprint('home', __name__)


@home_bp.route('/')
def splash():
    # Flask looks inside the 'templates' folder automatically
    return render_template('splash.html')


@home_bp.route('/index')
def index():
    return render_template('index.html')

@home_bp.route('/about')
def about():
    return render_template('about.html')


@home_bp.route('/help')
def help_page():
    return render_template('help.html')
@home_bp.route('/send-message', methods=['POST'])
def send_message():
    message = request.form['message']

    # temporary logic (no database yet)
    print("Message received:", message)

    return redirect(url_for('dashboard.dashboard'))



