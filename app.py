from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz.db'  # SQLite database URI
db = SQLAlchemy(app)

# Define database models
class Instructor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    quizzes = db.relationship('Quiz', backref='instructor', lazy=True)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey('instructor.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    questions = db.relationship('Question', backref='quiz', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    options = db.relationship('Option', backref='question', lazy=True)

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False)
    quiz_id = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)

class StudentResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_attempt_id = db.Column(db.Integer, nullable=False)
    question_id = db.Column(db.Integer, nullable=False)
    option_id = db.Column(db.Integer)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/instructor/dashboard')
def instructor_dashboard():
    instructors = Instructor.query.all()
    quizzes = Quiz.query.all()

    print(quizzes);
    return render_template('instructor_dashboard.html', instructors=instructors, quizzes=quizzes)

@app.route('/student/dashboard')
def student_dashboard():
    quizzes = Quiz.query.all()
    return render_template('student_dashboard.html', quizzes=quizzes)

@app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        # Process student responses
        pass
    return render_template('take_quiz.html', quiz=quiz)

# Route to handle quiz creation form submission
# Route to handle quiz creation form submission
@app.route('/create_quiz', methods=['POST'])
def create_quiz():
    with app.app_context():
        title = request.form['title']
        instructor_id = request.form['instructor_id']  # Assuming you have a hidden input field in the form for instructor_id
        print(f"Received title: {title}, instructor_id: {instructor_id}")

        quiz = Quiz(title=title, instructor_id=instructor_id)
        db.session.add(quiz)
        db.session.commit()
        print(f"Quiz added: {quiz}")

        # Loop through form fields to extract questions and options
        for field in request.form:
            if field.startswith('question'):
                question_text = request.form[field]
                print(f"Received question text: {question_text}")
                question = Question(text=question_text, quiz_id=quiz.id)
                db.session.add(question)
                db.session.commit()
                print(f"Question added: {question}")
                # Extract options for each question
                for option_field in request.form.getlist(field + '_options'):
                    option_text = request.form[option_field]
                    is_correct = option_field.endswith('_correct')
                    print(f"Received option text: {option_text}, is_correct: {is_correct}")
                    option = Option(text=option_text, is_correct=is_correct, question_id=question.id)
                    db.session.add(option)
                    db.session.commit()
                    print(f"Option added: {option}")

    return redirect(url_for('instructor_dashboard'))


# Student login page and logic
@app.route('/login/student', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Perform student login logic here (validate username and password)
        # For demonstration purposes, let's assume username and password are valid
        if username == 'student' and password == 'password':
            # Redirect to student dashboard upon successful login
            return redirect(url_for('student_dashboard'))
        else:
            # If login fails, display an error message
            error_message = 'Invalid username or password. Please try again.'
            return render_template('student_login.html', error_message=error_message)
    return render_template('student_login.html')


# Instructor login page and logic
@app.route('/login/instructor', methods=['GET', 'POST'])
def instructor_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Perform instructor login logic here (validate username and password)
        # For demonstration purposes, let's assume username and password are valid
        if username == 'instructor' and password == 'password':
            # Redirect to instructor dashboard upon successful login
            return redirect(url_for('instructor_dashboard'))
        else:
            # If login fails, display an error message
            error_message = 'Invalid username or password. Please try again.'
            return render_template('instructor_login.html', error_message=error_message)
    return render_template('instructor_login.html')

if __name__ == '__main__':
    app.run(debug=True)
