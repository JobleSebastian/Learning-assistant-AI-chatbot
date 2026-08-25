import json

class Student:

    def save(self):

        data = {
            "current_course": self.current_course,
            "course_outline": self.course_outline,
            "current_lesson": self.current_lesson,
            "completed_lessons": self.completed_lessons,
            "completed_lesson_contents": self.completed_lesson_contents,
            "quiz_score": self.quiz_score,
            "questions_answered": self.questions_answered,
            "flashcard_active": self.flashcard_active,
            "current_flashcard": self.current_flashcard,
            "current_flashcard_answer": self.current_flashcard_answer,
            "flashcard_status": self.flashcard_status,
            "difficult_flashcards": self.difficult_flashcards,
            "review_flashcard_index": self.review_flashcard_index,
            "quiz_active": self.quiz_active,
            "flashcard_history": self.flashcard_history,
            "quiz_results": self.quiz_results,
            "current_quiz_lesson": self.current_quiz_lesson,
            "flashcard_results": self.flashcard_results,
            "current_flashcard_lesson": self.current_flashcard_lesson,
            "lesson_learning_points": self.lesson_learning_points,
            "quiz_history": self.quiz_history
            
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
            self.completed_lesson_contents = data.get("completed_lesson_contents", [])
            self.quiz_score = data["quiz_score"]
            self.questions_answered = data.get("questions_answered", 0)
            self.last_quiz_lesson = ""
            self.flashcard_active = data.get("flashcard_active", False)
            self.current_flashcard = data.get("current_flashcard", "")
            self.current_flashcard_answer = data.get("current_flashcard_answer", "")
            self.flashcard_status = data.get("flashcard_status", None)
            self.difficult_flashcards = data.get("difficult_flashcards", [])
            self.review_flashcard_index = data.get("review_flashcard_index", -1)
            self.quiz_history = data.get("quiz_history", [])
            self.flashcard_history = data.get("flashcard_history", [])
            self.flashcard_results = data.get("flashcard_results", [])
            self.current_flashcard_lesson = data.get("current_flashcard_lesson", "")
            self.quiz_results = data.get("quiz_results", [])
            self.lesson_learning_points = data.get("lesson_learning_points",{})
            self.current_quiz_lesson = data.get("current_quiz_lesson", "")
          
            
        except FileNotFoundError:

            pass

    def __init__(self):

        self.name = ""

        self.current_course = None

        self.course_outline = []

        self.current_lesson = 0

        self.completed_lessons = []

        self.completed_lesson_contents = []

        self.quiz_score = 0

        self.questions_answered = 0

        self.current_question = ""

        self.current_options = []

        self.correct_answer = ""

        self.explanation = ""

        self.quiz_active = False

        self.flashcard_active = False

        self.current_flashcard = ""

        self.current_flashcard_answer = ""

        self.flashcard_status = None

        self.difficult_flashcards = []

        self.review_flashcard_index = -1

        self.quiz_history = []

        self.flashcard_history = []

        self.flashcard_results = []

        self.current_flashcard_lesson = ""

        self.quiz_results = []

        self.current_quiz_lesson = ""

        self.lesson_learning_points = {}

        self.quiz_answer_positions = []

        self.streak = 0

    def reset_course(self):

        self.current_course = None

        self.course_outline = []

        self.current_lesson = 0

        self.completed_lessons = []

        self.completed_lesson_contents = []

        self.questions_answered = 0

        self.quiz_score = 0

        self.quiz_history = []

        self.quiz_active = False

        self.current_question = ""

        self.correct_answer = ""

        self.explanation = ""

        self.last_quiz_lesson = ""

        self.flashcard_active = False

        self.current_flashcard = ""

        self.current_flashcard_answer = ""

        self.flashcard_status = None

        self.difficult_flashcards = []

        self.review_flashcard_index = -1

        self.flashcard_history = []

        self.quiz_results = []

        self.current_quiz_lesson = ""

        self.flashcard_results = []

        self.current_flashcard_lesson = ""

        self.lesson_learning_points = {}

        self.quiz_answer_positions = []