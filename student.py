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

        self.streak = 0

    def reset_course(self):

        self.current_course = None

        self.course_outline = []

        self.current_lesson = 0

        self.completed_lessons = []

        self.quiz_score = 0