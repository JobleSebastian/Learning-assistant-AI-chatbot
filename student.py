import json

class Student:

    def save(self):

        data = {
            "current_course": self.current_course,
            "course_outline": self.course_outline,
            "current_lesson": self.current_lesson,
            "completed_lessons": self.completed_lessons,
            "quiz_score": self.quiz_score
        }

        with open("student.json", "w") as file:
            json.dump(data, file, indent=4)

    def load(self):

        try:

            with open("student.json", "r") as file:
                data = json.load(file)

            self.current_course = data["current_course"]
            self.course_outline = data["course_outline"]
            self.current_lesson = data["current_lesson"]
            self.completed_lessons = data["completed_lessons"]
            self.quiz_score = data["quiz_score"]

        except FileNotFoundError:

            pass
    def __init__(self):

        self.name = ""

        self.current_course = None

        self.course_outline = []

        self.current_lesson = 0

        self.completed_lessons = []

        self.quiz_score = 0

        self.quiz_score = 0

        self.current_question = ""

        self.current_options = []

        self.correct_answer = ""

        self.explanation = ""

        self.streak = 0

    def reset_course(self):

        self.current_course = None

        self.course_outline = []

        self.current_lesson = 0

        self.completed_lessons = []

        self.quiz_score = 0