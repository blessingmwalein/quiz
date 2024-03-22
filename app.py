from datetime import datetime

from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.orm import relationship

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_attempt.db'  # SQLite database URI
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

    def serialize(self):
        return {
            'id': self.id,
            'title': self.title,
            'instructor_id': self.instructor_id,
            'questions': [question.serialize() for question in self.questions]
        }


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    options = db.relationship('Option', backref='question', lazy=True)

    def serialize(self):
        return {
            'id': self.id,
            'question_text': self.question_text,
            'options': [option.serialize() for option in self.options]
        }


class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    def serialize(self):
        return {
            'id': self.id,
            'option_text': self.option_text,
            'is_correct': self.is_correct
        }


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class QuizAttempt(db.Model):
    __tablename__ = 'QuizAttempt'  # Specify the correct table name here
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)



class StudentResponse(db.Model):
    __tablename__ = 'StudentResponse'  # Specify the correct table name here
    id = db.Column(db.Integer, primary_key=True)
    quiz_attempt_id = db.Column(db.Integer, db.ForeignKey('QuizAttempt.id'), nullable=False)
    question_id = db.Column(db.Integer, nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey('option.id'))

    quiz_attempt = db.relationship('QuizAttempt', backref='responses')

    option = relationship('Option', primaryjoin='StudentResponse.option_id == Option.id', backref='student_responses')



# Routes for instructor dashboard and quizzes
@app.route('/instructor/dashboard')
def instructor_dashboard():
    instructors = Instructor.query.all()
    quizzes = Quiz.query.all()
    return render_template('instructor_dashboard.html', instructors=instructors, quizzes=quizzes)


@app.route('/api/instructor/quizzes')
def get_quizzes():
    instructor_id = request.args.get('instructor_id')
    print(instructor_id)
    if instructor_id:
        quizzes = Quiz.query.filter_by(instructor_id=instructor_id).all()
    else:
        quizzes = Quiz.query.all()
    serialized_quizzes = [quiz.serialize() for quiz in quizzes]
    return jsonify(serialized_quizzes)

@app.route('/create_quiz', methods=['POST'])
def create_quiz():
    data = request.get_json()
    title = data.get('title')
    instructor_id = data.get('instructor_id')
    questions = data.get('questions')

    if not (title and instructor_id and questions):
        return {'error': 'Missing required data'}, 400

    try:
        # Create quiz
        quiz = Quiz(title=title, instructor_id=instructor_id)
        db.session.add(quiz)
        db.session.commit()

        # Create questions and options
        for question_data in questions:
            question_text = question_data.get('question_text')
            options_data = question_data.get('options')

            if not (question_text and options_data):
                db.session.rollback()
                return {'error': 'Missing question or options data'}, 400

            question = Question(question_text=question_text, quiz_id=quiz.id)
            db.session.add(question)
            db.session.commit()

            for option_data in options_data:
                option_text = option_data.get('option_text')
                is_correct = option_data.get('is_correct')

                if not (option_text and isinstance(is_correct, bool)):
                    db.session.rollback()
                    return {'error': 'Invalid option data'}, 400

                option = Option(option_text=option_text, is_correct=is_correct, question_id=question.id)
                db.session.add(option)
                db.session.commit()

        return {'message': 'Quiz created successfully'}, 201
    except Exception as e:
        db.session.rollback()
        return {'error': str(e)}, 500


# API routes for student and instructor login
@app.route('/api/login/instructor', methods=['POST'])
def instructor_login_api():
    data = request.get_json()
    print(data)

    username = data.get('username')
    password = data.get('password')

    instructor = Instructor.query.filter_by(username=username, password=password).first()

    if instructor:
        return jsonify(
            {'success': True, 'message': 'Login successful', 'instructor': {
                'id': instructor.id,
                'username': instructor.username,
                # Add other instructor details here if needed
            }, 'redirect_url': url_for('instructor_dashboard')})
    else:
        return jsonify({'success': False, 'message': 'Invalid username or password. Please try again.'})


@app.route('/api/quiz/<int:quiz_id>/submit', methods=['POST'])
def submit_quiz_response(quiz_id):
    data = request.get_json()
    student_id = data.get('student_id')  # Assuming you have the student ID from the frontend
    responses = data.get('responses')  # Assuming responses are in the format: [{'question_id': 1, 'option_id': 2}, ...]

    if not (student_id and responses):
        return jsonify({'error': 'Missing required data'}), 400

    try:
        # Create QuizAttempt record
        quiz_attempt = QuizAttempt(student_id=student_id, quiz_id=quiz_id, start_time=datetime.now())
        db.session.add(quiz_attempt)
        db.session.commit()

        # Create StudentResponse records
        for response in responses:
            question_id = response.get('question_id')
            option_id = response.get('option_id')
            if not (question_id and option_id):
                db.session.rollback()
                return jsonify({'error': 'Invalid response data'}), 400

            student_response = StudentResponse(quiz_attempt_id=quiz_attempt.id, question_id=question_id, option_id=option_id)
            db.session.add(student_response)

        db.session.commit()
        summary_url = url_for('view_quiz_summary', quiz_id=quiz_id, student_id=student_id, _external=True)

        # Return JSON response with the URL
        return jsonify({'message': 'Quiz response submitted successfully', 'summary_url': summary_url}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
@app.route('/api/quiz/<int:quiz_id>/summary')
def get_quiz_summary(quiz_id):
    try:
        quiz = Quiz.query.get_or_404(quiz_id)
        questions = quiz.questions
        summary_data = []

        for question in questions:


            options = Option.query.filter_by(question_id=question.id).all()
            responses = StudentResponse.query.filter_by(question_id=question.id).all()
            response_data = []

            for response in responses:
                option = next((opt for opt in options if opt.id == response.option_id), None)
                selected_option = {
                    'option_id': option.id,
                    'option_text': option.option_text,
                    'is_correct': option.is_correct
                }
                student_response = {
                    'student_id': response.quiz_attempt.student_id,
                    'options': [{'option_id': opt.id, 'option_text': opt.option_text, 'is_correct' : opt.is_correct} for opt in options],
                    'option_text': response.option.option_text,
                    'selectedOption':   selected_option,

                }
                response_data.append(student_response)

            summary_data.append({
                'question_id': question.id,
                'question_text': question.question_text,
                'responses': response_data
            })

        return jsonify({'quiz_id': quiz_id, 'questions': summary_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/quiz/<int:quiz_id>/instructor')
def get_quiz_instructor(quiz_id):
    try:
        quiz = Quiz.query.get_or_404(quiz_id)
        questions = quiz.questions
        summary_data = []

        for question in questions:
            options = Option.query.filter_by(question_id=question.id).all()
            responses = StudentResponse.query.filter_by(question_id=question.id).all()
            response_data = []

            for response in responses:
                option = next((opt for opt in options if opt.id == response.option_id), None)
                selected_option = {
                    'option_id': option.id,
                    'option_text': option.option_text,
                    'is_correct': option.is_correct
                }
                student_id = response.quiz_attempt.student_id
                marks = get_student_marks(student_id, question.id)  # Calculate total marks for the student
                student_response = {
                    'student_id': student_id,
                    'student_name': Student.query.get(student_id).username,  # Get student's username
                    'options': [{'option_id': opt.id, 'option_text': opt.option_text, 'is_correct': opt.is_correct} for
                                opt in options],
                    'option_text': response.option.option_text,
                    'selectedOption': selected_option,
                    'marks': marks  # Add marks to the response
                }
                response_data.append(student_response)

            summary_data.append({
                'question_id': question.id,
                'question_text': question.question_text,
                'responses': response_data
            })

        return jsonify({'quiz_id': quiz_id, 'questions': summary_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_student_marks(student_id, question_id):
    # Fetch all quiz attempts for the given student
    quiz_attempts = QuizAttempt.query.filter_by(student_id=student_id).all()

    # Initialize total marks
    total_marks = 0

    # Iterate through each quiz attempt
    for attempt in quiz_attempts:
        # Fetch the response for the given question in this attempt
        response = StudentResponse.query.filter_by(quiz_attempt_id=attempt.id, question_id=question_id).first()

        # If response exists and is correct, increment total marks
        if response and response.option.is_correct:
            total_marks += 1

    return total_marks

@app.route('/login/instructor', methods=['GET'])
def instructor_login():
    return render_template('instructor_login.html')

@app.route('/quiz/<int:quiz_id>/instructor', methods=['GET'])
def view_quiz_submit(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        # Process student responses
        pass
    return render_template('view_quiz_submit.html', quiz=quiz)


@app.route('/quiz/<int:quiz_id>/summary', methods=['GET'])
def view_quiz_summary(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        # Process student responses
        pass
    return render_template('view_quiz_summary.html', quiz=quiz)
@app.route('/login/student', methods=['GET'])
def student_login():
    return render_template('student_login.html')

@app.route('/api/login/student', methods=['POST'])
def student_login_api():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    student = Student.query.filter_by(username=username, password=password).first()

    if student:
        return jsonify({'success': True, 'message': 'Login successful', 'student': {
            'id': student.id,
            'username': student.username,
            # Add other student details here if needed
        }, 'redirect_url': url_for('student_dashboard')})
    else:
        return jsonify({'success': False, 'message': 'Invalid username or password. Please try again.'})


# Student dashboard route

@app.route('/student/dashboard')
def student_dashboard():
    quizzes = Quiz.query.all()
    return render_template('student_dashboard.html', quizzes=quizzes)


@app.route('/')
def index():
    return render_template('index.html')
# Route to view and take quiz
@app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        # Process student responses
        pass
    return render_template('take_quiz.html', quiz=quiz)


if __name__ == '__main__':
    app.run(debug=True)
