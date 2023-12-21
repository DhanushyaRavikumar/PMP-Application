# import flask modules
from flask import Flask, url_for, render_template, request,redirect,flash, abort, session, send_file
import sqlite3
import datetime as dt
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import create_engine, text, func
import bcrypt
import pandas as pd
import json
import plotly
import plotly.graph_objs as go
import pymysql
import os
from werkzeug.utils import secure_filename
import uuid
from sqlalchemy.exc import IntegrityError
from google.cloud import storage

# instance of flask application
app = Flask(__name__)
app.secret_key = 'aef2f0e3683344d0991eaeb046d983eb'
con_string = "mysql+pymysql://user:12345678@35.200.233.26/gwcpmpnew"
app.config["SQLALCHEMY_DATABASE_URI"] = con_string
engine = create_engine(con_string)
db = SQLAlchemy(app)
app.app_context().push()
credentials_path = 'static/keys/teqcertify-b938b49108a3.json'
storage_client = storage.Client.from_service_account_json(credentials_path)
BUCKET_NAME = 'pmp-bucket'
USER_DP_FOLDER = 'user_dp/' 

#form models
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=250)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

project_members = db.Table(
    'project_members',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
)

# Database Models
class Users(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    Email = db.Column(db.String(250), unique=True, nullable=False)
    Name = db.Column(db.String(250), nullable=False)
    User_Role = db.Column(db.String(250), default='Member', nullable=False)
    Password = db.Column(db.String(250), nullable=False)
    Designation = db.Column(db.String(250), nullable=False)
    Creation_Date = db.Column(db.DateTime(), default=dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30), nullable=False)
    AvatarID = db.Column(db.String(250), default='user.png', nullable=True)

    # Define the many-to-many relationship
    projects = db.relationship('Project', secondary=project_members, backref=db.backref('users_in_projects', lazy='dynamic'))
    def __repr__(self):
        return str(self.id)    

class Project(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    ProjectName = db.Column(db.String(250), nullable=False)
    ProjectOwner = db.Column(db.String(250), nullable=False)
    ProjectDescription = db.Column(db.Text)
    ProjectManager = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    CreatedBy = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    StartDate = db.Column(db.Date(), nullable=False)
    EndDate = db.Column(db.Date(), nullable=False)
    CreationDate = db.Column(db.DateTime(), default=dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30), nullable=False)
    # Use 'users_projects'
    users = db.relationship('Users', secondary=project_members, backref=db.backref('projects_users', lazy='dynamic'))

    def __repr__(self):
        return str(self.id)
    
class Epic(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    EpicName = db.Column(db.String(250), nullable=False)
    EpicDescription = db.Column(db.Text)
    CreatedBy = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    StartDate = db.Column(db.Date(), nullable=False)
    EndDate = db.Column(db.Date(), nullable=False)
    CreationDate = db.Column(db.DateTime(), default=dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30), nullable=False)
    ProjectID = db.Column(db.Integer(), db.ForeignKey('project.id'), nullable=False)

    def __repr__(self):
        return 'epic.id'

class Story(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    StoryName = db.Column(db.String(250), nullable=False)
    StoryDescription = db.Column(db.Text)
    CreatedBy = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    StartDate = db.Column(db.Date(), nullable=False)
    EndDate = db.Column(db.Date(), nullable=False)
    CreationDate = db.Column(db.DateTime(), default=dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30), nullable=False)
    EpicID= db.Column(db.Integer(), db.ForeignKey('epic.id'), nullable=False)

    def __repr__(self):
        return 'story.id'

class Subtask(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    SubtaskName = db.Column(db.String(250), nullable=False)
    SubtaskDescription = db.Column(db.Text)
    AssignedTo = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    CreatedBy = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    StartDate = db.Column(db.Date(), nullable=False)
    EndDate = db.Column(db.Date(), nullable=False)
    CreationDate = db.Column(db.DateTime(), nullable=False)
    Status = db.Column(db.String(250), default='InProgress', nullable=False)
    Type = db.Column(db.String(250), default='Task', nullable=False)
    Priority = db.Column(db.String(250), default='Medium', nullable=False)
    StoryID = db.Column(db.Integer(), db.ForeignKey('story.id'), nullable=False)
    discussions = db.relationship('Discussion', backref='subtask', foreign_keys='Discussion.SubtaskID', lazy=True)
    CompletionTime = db.Column(db.DateTime())
    CreatedByUser = db.relationship('Users', foreign_keys='Subtask.CreatedBy')

    def __repr__(self):
        return 'subtask.id'

class Discussion(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    SubtaskID = db.Column(db.Integer(), db.ForeignKey('subtask.id'), nullable=False)
    Comment = db.Column(db.Text, nullable=False)
    Timestamp = db.Column(db.DateTime(), nullable=False)
    Sent = db.Column(db.Boolean(), default=False, nullable=False)
    Seen = db.Column(db.Boolean(), default=False, nullable=False)
    user = db.relationship('Users', backref='discussions')

    def __repr__(self):
        return 'discussion.id'

#Public User Restrictions    
@app.before_request
def require_login():
    allowed_routes = ['login','static', 'show_register']  # add any route that doesn't require login here
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))

#Member Restrictions
@app.before_request
def restrict_access_member():
    user_id = session.get('user_id')
    if user_id:
        user = Users.query.filter_by(id=user_id).first()
        if user.User_Role == 'Member':
            restricted_functions = ['add_project', 'add_epic', 'add_story', 'add_subtask', 'update_project', 'update_epic', 'update_story',
                                     'update_subtask', 'delete_subtask', 'delete_story', 'delete_epic','show_projects','project_details',
                                     'story_details','epic_details', 'show_users','update_user_role', 'show_all_subtask_status', 'delete_project', 'show_mt_home']
            if request.endpoint in restricted_functions:
                abort(403)  # Forbidden

#TeamLead Restrcitions
@app.before_request
def restrict_access_teamlead():
    user_id = session.get('user_id')
    if user_id:
        user = Users.query.filter_by(id=user_id).first()
        if user.User_Role == 'Team Lead':
            restricted_functions = ['add_project', 'add_epic', 'add_story', 'update_project', 'update_epic', 'update_story', 'delete_story',
                                     'delete_epic','show_users','update_user_role', 'delete_project']
            if request.endpoint in restricted_functions:
                abort(403)  # Forbidden

#Manager Restrcitions
@app.before_request
def restrict_access_manager():
    user_id = session.get('user_id')
    if user_id:
        user = Users.query.filter_by(id=user_id).first()
        if user.User_Role == 'Manager':
            restricted_functions = ['add_project', 'update_project','show_users','update_user_role','delete_project']
            if request.endpoint in restricted_functions:
                abort(403)  # Forbidden
#Injecting User Info to all pages
@app.context_processor
def inject_user():
    def get_user():
        if 'user_id' in session:
            user = Users.query.get(session['user_id'])
            return user
        return None
    return {'user': get_user()}

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        flash('You have been Logged in Successfully!!', 'success')
        return redirect(url_for('show_user_home'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Users.query.filter_by(Email=email).first()
        
        if user:
            try:
                if bcrypt.checkpw(password.encode('utf-8'), user.Password.encode('utf-8')):
                    session['user_id'] = user.id
                    flash('You have been Logged in Successfully!!', 'success')
                    return redirect(url_for('show_user_home'))
                else:
                    flash('Invalid Email or Password Combination', 'danger')
            except ValueError:
                flash('Invalid Password Hash Format', 'danger')
        else:
            flash('Invalid Email or Password Combination', 'danger')
    
    form = LoginForm()
    return render_template('login_page.html', form=form)

@app.route('/register', methods=['POST','GET'])
def show_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        designation = request.form['designation']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        user_role = request.form['user_role']
        creation_date = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)
    
        allowed_domains = ['gwcdata.ai', 'teqcertify.com']
        if not any(email.endswith(domain) for domain in allowed_domains):
            flash('Only gwcteq.com and teqcertify.com emails are allowed to register', 'warning')
            return redirect(url_for('show_register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'warning')
            return redirect(url_for('show_register'))
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        existing_user = Users.query.filter_by(Email=email).first()
        if existing_user:
            flash('A user with the same email already exists. Please use a different email.', 'warning')
            return redirect(url_for('show_register'))
        
        try:
            user = Users(Email=email, Name=name, Password=hashed_password, Designation=designation, User_Role=user_role, Creation_Date=creation_date)
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('A user with the same email already exists. Please use a different email.', 'warning')
            return redirect(url_for('show_register'))
        
        flash('You have been Successfully Registered! You can now login!!', 'success')
        return redirect(url_for('login'))
    else:
        return render_template('register_page.html')
    
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully','success')
    return redirect(url_for('login'))

@app.route('/user_home', methods=['GET', 'POST'])
def show_user_home():
    projects_data = Project.query.all()
    subtask = Subtask.query.all()
    project_query = 'SELECT * FROM project'
    epic_query = 'SELECT * FROM epic'
    story_query = 'SELECT * FROM story'
    subtask_query = 'SELECT * FROM subtask'
    users_query = 'SELECT * FROM users'
    project_df = pd.read_sql_query(sql=text(project_query), con=engine.connect())
    epic_df = pd.read_sql_query(sql=text(epic_query), con=engine.connect())
    story_df = pd.read_sql_query(sql=text(story_query), con=engine.connect())
    subtask_df = pd.read_sql_query(sql=text(subtask_query), con=engine.connect())
    users_df = pd.read_sql_query(sql=text(users_query), con=engine.connect())
    total_unique_projects = project_df["id"].nunique()
    total_unique_epics = epic_df["id"].nunique()
    total_unique_stories = story_df["id"].nunique()
    total_unique_subtasks = subtask_df["id"].nunique()
    role_counts = users_df['User_Role'].value_counts()
    trace = go.Pie(
    labels=role_counts.index,
    values=role_counts.values,
    hole=0.5,
    marker=dict(colors=['#F44336', '#FFEB3B', '#4CAF50', '#2196F3']),
)
    user_role = go.Figure(data=[trace])
    user_role_json = user_role.to_json()
    # convert the StartDate column to datetime
    subtask_df['StartDate'] = pd.to_datetime(subtask_df['StartDate'])

    # filter the data to only include the last 30 days
    last_30_days = dt.datetime.now() - dt.timedelta(days=30)
    subtask_count = subtask_df[subtask_df['StartDate'] >= last_30_days]

    # group the data by date and count the number of subtasks for each date
    subtasks_by_date = subtask_df.groupby(subtask_df['StartDate'].dt.date).count()['id']

    # create the line chart with data labels and lines
    trace = go.Scatter(
        x=subtasks_by_date.index,
        y=subtasks_by_date.values,
        mode='lines+markers+text',
        name='Subtasks',
        text=subtasks_by_date.values,
        textposition='top center',
        textfont=dict(size=10, color='black')
    )
    layout = go.Layout(
        xaxis=dict(title='Date'),
        yaxis=dict(title='Subtasks'),
        plot_bgcolor='white'
    )
    subtask_fig = go.Figure(data=[trace], layout=layout)
    subtask_fig_json = subtask_fig.to_json()
    user = None
    if 'user_id' in session:
        user_id = session['user_id']
        user = Users.query.filter_by(id=user_id).first()
        if user.User_Role == 'Member':
            assigned_subtasks_inprogress = Subtask.query.filter_by(AssignedTo=user_id).filter_by(Status='InProgress').all()
            assigned_subtasks_complete = Subtask.query.filter_by(AssignedTo=user_id).filter_by(Status='Complete').all()
            subtask_assigned_to_users = [Users.query.get(subtaskone.CreatedBy).Name for subtaskone in subtask]
            # Fetch the project names for assigned subtasks in progress
            assigned_subtasks_inprogress_with_project = []
            for subtask in assigned_subtasks_inprogress:
                project_name = (Project.query.join(Epic).join(Story, Epic.id == Story.EpicID).filter(Story.id == subtask.StoryID).first().ProjectName)

                assigned_subtasks_inprogress_with_project.append((subtask, project_name))
            
            # Fetch the project names for assigned completed subtasks
            assigned_subtasks_complete_with_project = []
            for subtask in assigned_subtasks_complete:
                project_name = (Project.query.join(Epic).join(Story, Epic.id == Story.EpicID).filter(Story.id == subtask.StoryID).first().ProjectName)


                assigned_subtasks_complete_with_project.append((subtask, project_name))
            
            return render_template('member_home.html',
                                   projects=projects_data,
                                   user=user, subtask=subtask,
                                   assigned_subtasks_inprogress=assigned_subtasks_inprogress_with_project,
                                   assigned_subtasks_complete=assigned_subtasks_complete_with_project, subtask_assigned_to_users= subtask_assigned_to_users)
        
    return render_template('dashboard.html', projects=projects_data, total_unique_projects = total_unique_projects, total_unique_epics = total_unique_epics, total_unique_stories = total_unique_stories, total_unique_subtasks = total_unique_subtasks, user_role_json=user_role_json, subtask_fig_json=subtask_fig_json)

@app.route('/mt_home')
def show_mt_home():
    if 'user_id' in session:
        user_id = session['user_id']
        user = Users.query.filter_by(id=user_id).first()

        # initialize the variable
        assigned_subtasks_inprogress = []
        assigned_subtasks_complete = []
        subtask_assigned_to_users = []
        assigned_subtasks_inprogress_with_project = []
        assigned_subtasks_complete_with_project = []

        if user.User_Role in ['Manager', 'Admin', 'Team Lead']:
            assigned_subtasks_inprogress = Subtask.query.filter_by(AssignedTo=user.id).filter_by(Status='InProgress').all()
            assigned_subtasks_complete = Subtask.query.filter_by(AssignedTo=user.id).filter_by(Status='Complete').all()

            if assigned_subtasks_inprogress:
                subtask_assigned_to_users = [Users.query.get(subtaskone.CreatedBy).Name for subtaskone in assigned_subtasks_inprogress]

                for subtask in assigned_subtasks_inprogress:
                    project_name = (Project.query.join(Epic).join(Story, Epic.id == Story.EpicID).filter(Story.id == subtask.StoryID).first().ProjectName)
                    assigned_subtasks_inprogress_with_project.append((subtask, project_name))

            if assigned_subtasks_complete:
                for subtask in assigned_subtasks_complete:
                    project_name = (Project.query.join(Epic).join(Story, Epic.id == Story.EpicID).filter(Story.id == subtask.StoryID).first().ProjectName)
                    assigned_subtasks_complete_with_project.append((subtask, project_name))

    return render_template('MT_home.html',
                           user=user,
                           assigned_subtasks_inprogress=assigned_subtasks_inprogress_with_project,
                           assigned_subtasks_complete=assigned_subtasks_complete_with_project,
                           subtask_assigned_to_users=subtask_assigned_to_users)

@app.route('/projects')
def show_projects():
    if 'user_id' not in session:
        flash('You need to log in first', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = Users.query.get(user_id)

    projects_data = []
    if user.User_Role == 'Admin':
        projects_data = Project.query.all()
    elif user.User_Role == 'Manager':
        projects_data = Project.query.filter_by(ProjectManager=user_id).all()
    elif user.User_Role == 'Team Lead':
        projects_data = Project.query.filter(Project.users.any(id=user_id)).all()

    project_managers = {}
    created_by_users = {}

    for project in projects_data:
        project_manager = Users.query.get(project.ProjectManager)
        created_by_user = Users.query.get(project.CreatedBy)
        project_managers[project.id] = project_manager.Name
        created_by_users[project.id] = created_by_user.Name

    return render_template('home_project.html', projects=projects_data, project_managers=project_managers, created_by_users=created_by_users)

#USER CONTROL PAGE FOR ADMIN
@app.route('/user_control')
def show_users():
    users_data = Users.query.all()
    return  render_template('user_role_control.html', users= users_data)

@app.route('/update_user_role/<int:user_id>/<new_role>')
def update_user_role(user_id, new_role):
    user = Users.query.get(user_id)
    user.User_Role = new_role
    db.session.commit()
    return 'User role updated successfully'

#USER PROFILE FOR ALL USERS
@app.route('/user_profile')
def show_user_profile():
    if 'user_id' in session:
        user_id = session['user_id']
        user = Users.query.filter_by(id=user_id).first()
    return  render_template('user_profile.html', user= user)

#UPDATE PASSWORD
@app.route('/update_password', methods=['POST'])
def update_password():
    if 'user_id' in session:
        user_id = session['user_id']
        user = Users.query.filter_by(id=user_id).first()
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Check if the old password entered by the user is correct
        if not bcrypt.checkpw(old_password.encode('utf-8'), user.Password.encode('utf-8')):
            flash('Invalid Old Password', 'danger')
            return redirect(url_for('show_user_profile'))

        # Check if the new password and confirm password match
        if new_password != confirm_password:
            flash('New Password and Confirm Password do not match', 'danger')
            return redirect(url_for('show_user_profile'))

        # Hash the new password and update the user's password in the database
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        user.Password = hashed_password
        db.session.commit()

        flash('Password Updated Successfully', 'success')
        return redirect(url_for('show_user_profile'))
    else:
        return redirect(url_for('login'))

# CREATE ROUTES FOR ALL HIERARCHIES
@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        designation = request.form['designation']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        user_role = request.form['user_role']
        creation_date = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)

        if not email.endswith('@gwcteq.com'):
            flash('Only gwcteq.com emails are allowed to register', 'warning')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match', 'warning')
            return redirect(url_for('register'))

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        user = Users(name=name, email=email, designation=designation, password=hashed_password,
                    user_role=user_role, creation_date=creation_date)
        db.session.add(user)
        db.session.commit()

        flash('You have been Successfully Registered! You can now login!!', 'success')
        return redirect(url_for('login'))
    else:
        return render_template('register_page.html')

@app.route('/add_project', methods=['POST', 'GET'])
def add_project():
    managers = Users.query.filter_by(User_Role='Manager').all()
    admins = Users.query.filter_by(User_Role='Admin').all()
    proj_users = Users.query.all()
#   members = Users.query.filter_by(User_Role='Member').all()
#   team_lead = Users.query.filter_by(User_Role='Team Lead').all()
    if 'user_id' in session:
        user_id = session['user_id']
        user = Users.query.filter_by(id=user_id).first()
    if request.method == 'POST':
        name = request.form['name']
        owner = request.form['owner']
        description = request.form['description']
        manager = request.form['manager']
        createdby = user.id
        member_ids = request.form.getlist('members')
        start_date = dt.datetime.strptime(request.form['start-date'], '%Y-%m-%d').date()
        end_date = dt.datetime.strptime(request.form['end-date'], '%Y-%m-%d').date()
        creation_date = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)

        # Create the project instance
        project = Project(
            ProjectName=name,
            ProjectOwner=owner,
            ProjectDescription=description,
            ProjectManager=manager,
            CreatedBy=createdby,
            StartDate=start_date,
            EndDate=end_date,
            CreationDate=creation_date
        )

        db.session.add(project)
        db.session.commit()

        # Add members to the project
        for member_id in member_ids:
            member_id = Users.query.filter_by(id=member_id).first()
            if member_id:
                project.users.append(member_id)

        db.session.commit()

        flash('Your Project has been Created Successfully!!', 'success')
        return redirect(url_for('show_projects'))
    else:
        return render_template('create_project.html', Managers=managers, Admins=admins, proj_users= proj_users, user=user)

@app.route('/add_epic/<int:project_id>', methods=['GET', 'POST'])
def add_epic(project_id):
    if 'user_id' in session:
        user_id = session['user_id']
        user = Users.query.filter_by(id=user_id).first()
    if request.method == 'POST':
        epic_name = request.form['epic_name']
        created_by = user.id
        epic_description = request.form['epic_description']
        start_date = dt.datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = dt.datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        creationDate = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)
        
        # add the epic to the database with the project ID
        epic = Epic(EpicName=epic_name, CreatedBy=created_by, EpicDescription=epic_description,
                    StartDate=start_date, EndDate=end_date, CreationDate = creationDate, ProjectID=project_id)
        db.session.add(epic)
        db.session.commit()
        flash('Epic has been successfully added to the Project!!', 'success')
        return redirect(url_for('project_details', project_id=project_id))
    
    return render_template('create_epic.html', project_id=project_id, user=user)

@app.route('/add_story/<int:epic_id>', methods=['GET', 'POST'])
def add_story(epic_id):
    if 'user_id' in session:
        user_id = session['user_id']
        user = Users.query.filter_by(id=user_id).first()
    if request.method == 'POST':
        story_name = request.form['story_name']
        created_by = user.id
        story_description = request.form['story_description']
        start_date = dt.datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = dt.datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        creationDate = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)
        
        # add the story to the database with the epic ID
        story = Story(StoryName=story_name, CreatedBy=created_by, StoryDescription=story_description,
                      StartDate=start_date, EndDate=end_date, CreationDate = creationDate, EpicID=epic_id)
        db.session.add(story)
        db.session.commit()
        
        epic = Epic.query.filter_by(id=epic_id).first()
        flash('UserStory has been added Successfully', 'success')
        return redirect(url_for('epic_details', epic_id=epic_id))
    
    return render_template('create_story.html', epic_id=epic_id, user=user)

@app.route('/add_subtask/<int:story_id>', methods=['GET', 'POST'])
def add_subtask(story_id):
    story = Story.query.filter_by(id=story_id).first()
    epic = Epic.query.get(story.EpicID)
    project = Project.query.get(epic.ProjectID)
    all_users = project.users
    if 'user_id' in session:
        user_id = session['user_id']
        user = Users.query.filter_by(id=user_id).first()
    if request.method == 'POST':
        subtask_name = request.form['subtask_name']
        created_by = user.id
        subtask_description = request.form['subtask_description']
        start_date = dt.datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = dt.datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        assigned_to = request.form['assigned_to']
        subtask_priority = request.form['subtask_priority']
        subtask_type = request.form['subtask_type']
        creation_date = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)

        # Add the subtask to the database with the story ID
        subtask = Subtask(
            SubtaskName=subtask_name,
            CreatedBy=created_by,
            SubtaskDescription=subtask_description,
            AssignedTo=assigned_to,
            StartDate=start_date,
            EndDate=end_date,
            CreationDate=creation_date,
            Type=subtask_type,
            Priority=subtask_priority,
            StoryID=story_id
        )
        db.session.add(subtask)
        db.session.commit()

        story = Story.query.filter_by(id=story_id).first()
        flash('SubTask has been added successfully', 'success')
        return redirect(url_for('story_details', story_id=story_id))

    return render_template('create_subtask.html', story_id=story_id, user=user, all_users=all_users)

#DETAILS ROUTE
@app.route('/project/<int:project_id>', methods=['POST', 'GET'])
def project_details(project_id):
    project = Project.query.get_or_404(project_id)
    epics_data = Epic.query.filter_by(ProjectID=project_id).all()

    project_manager = Users.query.get(project.ProjectManager)
    created_by_user = Users.query.get(project.CreatedBy)
    epic_created_by_users = [Users.query.get(epic.CreatedBy) for epic in epics_data]

    # Zip epics_data and epic_created_by_users together
    epic_data_with_users = zip(epics_data, epic_created_by_users)
    
    return render_template('project_details.html', project=project, epics=epics_data, project_name=project.ProjectName, project_manager=project_manager, created_by_user=created_by_user,epic_data_with_users=epic_data_with_users,)

@app.route('/epic/<int:epic_id>', methods=['GET'])
def epic_details(epic_id):
    epic = Epic.query.get_or_404(epic_id)
    project = Project.query.get_or_404(epic.ProjectID)
    stories_data = Story.query.filter_by(EpicID=epic_id).all()
    created_by_user = Users.query.get(epic.CreatedBy)
    story_created_by_users = [Users.query.get(story.CreatedBy) for story in stories_data]
    # Zip epics_data and epic_created_by_users together
    story_data_with_users = zip(stories_data, story_created_by_users)
    
    return render_template('epic_details.html', epic=epic, project_name=project.ProjectName, stories=stories_data, created_by_user=created_by_user, story_data_with_users=story_data_with_users)

@app.route('/story/<int:story_id>', methods=['GET'])
def story_details(story_id):
    story = Story.query.get_or_404(story_id)
    epic = Epic.query.get_or_404(story.EpicID)
    project = Project.query.get_or_404(epic.ProjectID)
    subtasks_data = Subtask.query.filter_by(StoryID=story_id).order_by(Subtask.CreationDate.desc()).all()
    created_by_user = Users.query.get(story.CreatedBy)
    subtask_assigned_to_users = [Users.query.get(subtask.AssignedTo) for subtask in subtasks_data]
    subtask_created_by_users = [Users.query.get(subtask.CreatedBy) for subtask in subtasks_data]
    # Zip subtasks_data, subtask_assigned_to_users, and subtask_created_by_users together
    subtask_data_with_users = zip(subtasks_data, subtask_assigned_to_users, subtask_created_by_users)
    return render_template('story_details.html', epic=epic, project=project, project_name=project.ProjectName, epic_name=epic.EpicName, story=story, subtasks=subtasks_data, created_by_user=created_by_user, subtask_data_with_users=subtask_data_with_users)

@app.route('/subtasks/<int:subtask_id>', methods=['GET', 'POST'])
def subtask_details(subtask_id):    
    subtask = Subtask.query.get_or_404(subtask_id)
    story = Story.query.get_or_404(subtask.StoryID)
    epic = Epic.query.get_or_404(story.EpicID)
    project = Project.query.get_or_404(epic.ProjectID)
    created_by_user = Users.query.get(subtask.CreatedBy)
    assigned_to_user = Users.query.get(subtask.AssignedTo)
    user_id = session['user_id']  # Retrieve the user ID from the session
    timestamp = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)
    user = None
    if 'user_id' in session:
        user_id = session['user_id']
        user = Users.query.filter_by(id=user_id).first()
        if user.User_Role == 'Member' and user.id != subtask.AssignedTo:
            abort(403)

    if request.method == 'POST':
        new_status = request.form['status']
        if new_status == "Complete":
            subtask.CompletionTime = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)
            flash("You have Marked the SubTask as Complete", 'success')
        elif new_status == "InProgress":
            subtask.CompletionTime = None
            flash("You have Marked the SubTask In Progress", 'warning')
        subtask.Status = new_status
        db.session.commit()
        return redirect(request.referrer)
    
    if request.method == 'POST':
        comment = request.form['comment']
        # Create a new discussion object
        discussion = Discussion(SubtaskID=subtask_id, UserID=user_id, Comment=comment, Timestamp=timestamp)
        # Add the discussion to the database
        db.session.add(discussion)
        db.session.commit()
        flash('Discussion added successfully.', 'success')
        return redirect(request.referrer)

    # Fetch the discussions for the subtask
    discussions = Discussion.query.filter_by(SubtaskID=subtask_id).all()

    for discussion in discussions:
        if discussion.UserID != user_id:
            discussion.Seen = True  # Update Seen status for discussions seen by the receiver
    db.session.commit()
        
    return render_template('subtask_details.html', subtask=subtask, epic=epic, project=project, story=story, user_id=user_id, project_name=project.ProjectName, epic_name=epic.EpicName, discussions=discussions, created_by_user = created_by_user, assigned_to_user = assigned_to_user)

@app.route('/subtask/<int:subtask_id>/discussion', methods=['GET', 'POST'])
def subtask_discussion(subtask_id):
    subtask = Subtask.query.get_or_404(subtask_id)
    story = Story.query.get_or_404(subtask.StoryID)
    epic = Epic.query.get_or_404(story.EpicID)
    project = Project.query.get_or_404(epic.ProjectID)
    user_id = session['user_id']
    created_by_user = Users.query.get(subtask.CreatedBy)
    assigned_to_user = Users.query.get(subtask.AssignedTo)
    timestamp = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)

    if request.method == 'POST':
        comment = request.form['comment']
        discussion = Discussion(SubtaskID=subtask_id, UserID=user_id, Comment=comment, Timestamp=timestamp, Sent=True)
        db.session.add(discussion)
        db.session.commit()
        flash('Discussion added successfully.', 'success')
        return redirect(request.referrer)

    discussions = Discussion.query.filter_by(SubtaskID=subtask_id).all()

    for discussion in discussions:
        if discussion.UserID != user_id:
            discussion.Seen = True  # Update Seen status for discussions seen by the receiver
    db.session.commit()

    return render_template('subtask_discussion.html', epic=epic, project=project, story=story, subtask=subtask, discussions=discussions, user_id=user_id, created_by_user= created_by_user, assigned_to_user =assigned_to_user)

@app.route('/subtask/<int:subtask_id>/add_comment', methods=['POST'])
def add_comment(subtask_id):
    comment = request.form.get('comment')
    user_id = session['user_id']
    subtask = Subtask.query.get_or_404(subtask_id)

    discussion = Discussion(UserID=user_id, SubtaskID=subtask_id, Comment=comment, Sent=True)
    db.session.add(discussion)
    db.session.commit()

    flash('Comment added successfully.', 'success')
    return redirect(url_for('subtask_discussion', subtask_id=subtask_id))

#DELETE ROUTES
@app.route('/project/<int:project_id>/delete_project', methods=['POST'])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)

    project.users.clear()

    # Delete discussions
    discussions = Discussion.query \
    .join(Subtask, Subtask.id == Discussion.SubtaskID) \
    .join(Story, Story.id == Subtask.StoryID) \
    .join(Epic, Epic.id == Story.EpicID) \
    .filter(Epic.ProjectID == project.id) \
    .all()
    for discussion in discussions:
        db.session.delete(discussion)

    # Delete subtasks
    subtasks = Subtask.query \
        .join(Story, Story.id == Subtask.StoryID) \
        .join(Epic, Epic.id == Story.EpicID) \
        .filter(Epic.ProjectID == project.id) \
        .all()
    for subtask in subtasks:
        db.session.delete(subtask)

    # Delete stories
    stories = Story.query \
        .join(Epic, Epic.id == Story.EpicID) \
        .filter(Epic.ProjectID == project.id) \
        .all()
    for story in stories:
        db.session.delete(story)

    # Delete epics
    epics = Epic.query.filter_by(ProjectID=project.id).all()
    for epic in epics:
        db.session.delete(epic)

    # Delete project
    db.session.delete(project)
    db.session.commit()

    flash('Project deleted successfully.', 'success')
    return redirect(url_for('show_projects'))

@app.route('/project/<int:project_id>/delete_epic/<int:epic_id>', methods=['POST'])
def delete_epic(project_id, epic_id):
    epic = Epic.query.get_or_404(epic_id)

    # Retrieve all the stories and subtasks that are linked to the epic
    stories = Story.query.filter_by(EpicID=epic.id).all()
    subtasks = Subtask.query.filter(Subtask.StoryID.in_([s.id for s in stories])).all()

    # Delete the subtasks first, then the stories, and finally the epic
    for subtask in subtasks:
        db.session.delete(subtask)
    for story in stories:
        db.session.delete(story)
    db.session.delete(epic)
    db.session.commit()

    flash('Epic deleted successfully.', 'success') 
    return redirect(url_for('project_details', project_id=project_id))

@app.route('/delete_story/<int:story_id>/',methods=['POST'])
def delete_story(story_id):
    # find the story to delete
    story = Story.query.filter_by(id=story_id).first()

    if story:
        # delete all of the subtasks associated with the story
        Subtask.query.filter_by(StoryID=story.id).delete()

        # delete the story from the database
        db.session.delete(story)
        db.session.commit()

        flash('UserStory deleted successfully','success')
    else:
        flash('UserStory not found', 'danger')

    return redirect(url_for('epic_details', epic_id=story.EpicID))

@app.route('/subtask/<int:subtask_id>/delete_subtask', methods=['POST'])
def delete_subtask(subtask_id):
    subtask = Subtask.query.get_or_404(subtask_id)
    db.session.delete(subtask)
    db.session.commit()
    flash('Subtask has been deleted.', 'success')
    return redirect(url_for('story_details', story_id=subtask.StoryID))

@app.route('/project/<int:project_id>/update_project', methods=['GET', 'POST'])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    managers = Users.query.filter_by(User_Role='Manager').all()
    admins = Users.query.filter_by(User_Role='Admin').all()
    proj_users = Users.query.all()

    # Get the selected member IDs for pre-selection
    member_ids = [user.id for user in project.users]

    if request.method == 'POST':
        # Retrieve form data
        project.ProjectName = request.form['ProjectName']
        project.ProjectOwner = request.form['ProjectOwner']
        project.ProjectDescription = request.form['ProjectDescription']
        project.ProjectManager = request.form['ProjectManager']
        member_ids = request.form.getlist('members')  # Get list of selected member IDs
        project.StartDate = dt.datetime.strptime(request.form['StartDate'], '%Y-%m-%d').date()
        project.EndDate = dt.datetime.strptime(request.form['EndDate'], '%Y-%m-%d').date()

        # Update the project and its members
        db.session.commit()

        # Clear existing members and add the selected members
        project.users.clear()
        for member_id in member_ids:
            member = Users.query.get(member_id)
            if member:
                project.users.append(member)
        db.session.commit()

        flash('Project details updated successfully!', 'success')
        return redirect(url_for('project_details', project_id=project.id))

    return render_template('update_project.html', project=project, Managers=managers, Admins=admins,
                           proj_users=proj_users, member_ids=member_ids)

@app.route('/epic/<int:epic_id>/update_epic', methods=['GET', 'POST'])
def update_epic(epic_id):
    epic = Epic.query.get_or_404(epic_id)
    if request.method == 'POST':
        epic.EpicName = request.form['EpicName']
        epic.EpicDescription = request.form['EpicDescription']
        epic.StartDate = dt.datetime.strptime(request.form['StartDate'], '%Y-%m-%d').date()
        epic.EndDate = dt.datetime.strptime(request.form['EndDate'], '%Y-%m-%d').date()
        db.session.commit()
        flash('Epic updated successfully!', 'success')
        return redirect(url_for('epic_details', epic_id=epic.id))
    return render_template('update_epic.html', epic=epic)

@app.route('/update_story/<int:story_id>', methods=['GET', 'POST'])
def update_story(story_id):
    story = Story.query.get(story_id)

    if request.method == 'POST':
        # Retrieve the updated values from the form and update the story object
        story.StoryName = request.form['StoryName']
        story.StoryDescription = request.form['StoryDescription']
        story.StartDate = dt.datetime.strptime(request.form['StartDate'], '%Y-%m-%d').date()
        story.EndDate = dt.datetime.strptime(request.form['EndDate'], '%Y-%m-%d').date()
        db.session.commit()

        # Redirect back to the story details page
        flash('UserStory has been Updated Sucessfully', 'success')
        return redirect(url_for('story_details', story_id=story.id))

    return render_template('update_story.html', story=story)

@app.route('/subtask/<int:subtask_id>/update_subtask', methods=['GET', 'POST'])
def update_subtask(subtask_id):
    subtask = Subtask.query.get(subtask_id)
    story = Story.query.get(subtask.StoryID)
    epic = Epic.query.get(story.EpicID)
    project = Project.query.get(epic.ProjectID)
    all_users = project.users
    created_by_user = Users.query.get(subtask.CreatedBy)
    if request.method == 'POST':
        subtask.SubtaskName = request.form.get('SubtaskName')
        subtask.SubtaskDescription = request.form.get('SubtaskDescription')
        if 'AssignedTo' in request.form:
            subtask.AssignedTo= request.form.get('AssignedTo')
        subtask.StartDate = dt.datetime.strptime(request.form['StartDate'], '%Y-%m-%d').date()
        subtask.EndDate = dt.datetime.strptime(request.form['EndDate'], '%Y-%m-%d').date()
        subtask.Type = request.form.get('SubtaskType')  # Update Subtask Type
        subtask.Priority = request.form.get('SubtaskPriority')  # Update Subtask Priority
        db.session.commit()
        flash('The SubTask has been updated successfully', 'success')
        return redirect(url_for('story_details', story_id=subtask.StoryID))

    return render_template('update_subtask.html', subtask=subtask, all_users=all_users, created_by_user= created_by_user)

#Subtask Status View
@app.route('/all_subtask_status')
def show_all_subtask_status():
    incomplete_subtasks = Subtask.query.filter(Subtask.Status == 'InProgress', Subtask.EndDate < dt.date.today()).all()
    incomplete_subtask_assigned_to_users = [Users.query.get(incomplete_subtask.AssignedTo) for incomplete_subtask in incomplete_subtasks]
    incomplete_subtask_created_by_users = [Users.query.get(incomplete_subtask.CreatedBy) for incomplete_subtask in incomplete_subtasks]
    incomplete_subtask_data_with_users = zip(incomplete_subtasks, incomplete_subtask_assigned_to_users, incomplete_subtask_created_by_users)
    
    in_progress_subtasks = Subtask.query.filter(Subtask.Status == 'InProgress', Subtask.EndDate >= dt.date.today()).all()
    in_progress_subtask_assigned_to_users = [Users.query.get(in_progress_subtask.AssignedTo) for in_progress_subtask in in_progress_subtasks]
    in_progress_subtask_created_by_users = [Users.query.get(in_progress_subtask.CreatedBy) for in_progress_subtask in in_progress_subtasks]
    in_progress_subtask_data_with_users = zip(in_progress_subtasks, in_progress_subtask_assigned_to_users, in_progress_subtask_created_by_users)
    
    completed_subtasks = Subtask.query.filter(Subtask.Status == 'Complete').all()
    completed_subtask_subtask_assigned_to_users = [Users.query.get(completed_subtask.AssignedTo) for completed_subtask in completed_subtasks]
    completed_subtask_created_by_users = [Users.query.get(completed_subtask.CreatedBy) for completed_subtask in completed_subtasks]
    completed_subtask_data_with_users = zip(completed_subtasks, completed_subtask_subtask_assigned_to_users, completed_subtask_created_by_users)

    return render_template('subtasks_all_status.html',
                           incomplete_subtask_data_with_users = incomplete_subtask_data_with_users,
                           in_progress_subtask_data_with_users = in_progress_subtask_data_with_users,
                           completed_subtask_data_with_users = completed_subtask_data_with_users
                           )

@app.route('/upload_picture', methods=['POST'])
def upload_picture():
    if 'user_id' in session:
        user_id = session['user_id']
        user = Users.query.filter_by(id=user_id).first()
        picture = request.files['profile_picture']
        remove_picture = request.form.get('remove_picture', 'false')

        if remove_picture == 'true':
            # Remove the profile picture if it's not the default 'user.png'
            if user.AvatarID != 'user.png':
                delete_blob(USER_DP_FOLDER + user.AvatarID)
                user.AvatarID = 'user.png'  # Set default picture
                db.session.commit()
                flash('Profile Picture Removed Successfully', 'success')
            else:
                flash('No picture to remove', 'danger')
        elif picture:
            # Delete the existing profile picture if it's not the default 'user.png'
            if user.AvatarID != 'user.png':
                delete_blob(USER_DP_FOLDER + user.AvatarID)

            # Generate a unique filename for the image
            filename = str(uuid.uuid4().hex) + secure_filename(picture.filename)

            # Upload the image to Google Cloud Storage in the 'user_dp' folder
            upload_blob(picture, USER_DP_FOLDER + filename)

            user.AvatarID = filename  # Save the filename in the AvatarID field
            db.session.commit()
            flash('Profile Picture Uploaded Successfully', 'success')
        else:
            flash('No picture selected', 'danger')

        return redirect(url_for('show_user_profile'))
    else:
        return redirect(url_for('login'))

def upload_blob(file_obj, destination_blob_name):
    """Uploads a file object to the bucket."""
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_file(file_obj, content_type=file_obj.content_type)

def delete_blob(blob_name):
    """Deletes a blob from the bucket."""
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)

    blob.delete()

@app.route('/user_dp/<filename>')
def get_user_dp(filename):
    # Construct the object path in the 'user_dp' folder
    object_path = f'user_dp/{filename}'

    # Retrieve the blob from the bucket
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(object_path)

    # Return the image as a response
    return send_file(blob.download_as_bytes(), mimetype=blob.content_type)

@app.errorhandler(404)
def custom_404(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def custom_500(error):
    return render_template('500.html'), 500

@app.errorhandler(403)
def custom_403(error):
    return render_template('403.html'), 403

if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0",port=8080)
