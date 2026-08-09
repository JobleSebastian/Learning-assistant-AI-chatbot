from prompts import QUIZ_PROMPT
import random

def help_command(chatbot):

    return """
Available Commands

/help        Show commands
/model       Current model
/history     Show conversation history
/clear       Clear conversation history
/reset       Reset course and conversation
/learn       Start a course
/progress    Show learning progress
/next        Continue to next lesson
"""

def parse_outline(outline):

    lessons = []

    for line in outline.split("\n"):

        line = line.strip()

        if not line:
            continue

        if "." in line:

            lesson = line.split(".", 1)[1].strip()

            lessons.append(lesson)

    return lessons

def clear_command(chatbot):

    chatbot.reset()

    return "Conversation cleared."

def history_command(chatbot):

    history = ""

    for msg in chatbot.messages:

        if msg["role"] == "system":
            continue

        history += f"{msg['role'].title()}: {msg['content']}\n\n"

    if history:
       return history

    if chatbot.student.current_course:

       return f"""
    Conversation history is empty.

    Current course : {chatbot.student.current_course.title()}

    Use /next to continue learning.
    """

    return "No conversation history."

def model_command(chatbot):

    return f"Current model: {chatbot.model}"

def learn_command(chatbot, command):

    parts = command.split(maxsplit=1)

    if len(parts) < 2:
        return "Usage: /learn <topic>"

    topic = parts[1]

    prompt = f"""
Create a beginner learning roadmap for {topic}.

Requirements:

- Return ONLY a numbered list of exactly 10 lessons.
- No explanations.
- No introductions.
- No conclusions.
- No markdown.
- No follow-up questions.
- No extra text.
"""

    outline = chatbot.ask(prompt)

    chatbot.student.current_course = topic
    chatbot.student.course_outline = parse_outline(outline)
    chatbot.student.current_lesson = 1
    chatbot.student.completed_lessons = []
    chatbot.student.completed_lesson_contents = []
    chatbot.student.questions_answered = 0
    chatbot.student.quiz_score = 0
    chatbot.student.save()

    return f"""
Course created!

Topic:
{topic.title()}

Course Outline

{outline}

Type /next to begin.
"""



def quiz_command(chatbot):

    if chatbot.student.current_course is None:
        return "Start a course first using /learn <topic>."

    if chatbot.student.current_lesson == 1:
        return "Complete the first lesson before taking a quiz."

    lesson_index = random.randrange(
        len(chatbot.student.completed_lessons)
    )
    
    lesson_title = chatbot.student.completed_lessons[
    lesson_index
    ]

    lesson_content = chatbot.student.completed_lesson_contents[
        lesson_index
    ]

    while (
        len(chatbot.student.completed_lessons) > 1
        and lesson_title == chatbot.student.last_quiz_lesson
    ):
        lesson_index = random.randrange(
            len(chatbot.student.completed_lessons)
        )

        lesson_title = chatbot.student.completed_lessons[
            lesson_index
        ]

        lesson_content = chatbot.student.completed_lesson_contents[
            lesson_index
        ]

    chatbot.student.last_quiz_lesson = lesson_title

    prompt = QUIZ_PROMPT.format(
        topic=chatbot.student.current_course,
        lesson_title=lesson_title,
        lesson_content=lesson_content
    )

    answer = chatbot.ask(prompt)

    chatbot.student.current_question = answer
    chatbot.student.quiz_active = True

    correct_start = answer.find("Correct Answer:")

    explanation_start = answer.find("Explanation:")

    correct = answer[
        correct_start + len("Correct Answer:"):
        explanation_start
    ].strip()

    chatbot.student.correct_answer = correct.strip().upper()

    explanation = answer[
        explanation_start + len("Explanation:")
    :].strip()

    chatbot.student.explanation = explanation

    question = answer[:correct_start].strip()

    return question
    
def answer_command(chatbot, command):

    if not chatbot.student.quiz_active:
        return "No active quiz. Use /quiz first."

    parts = command.split()

    if len(parts) < 2:
        return "Usage: /answer A"

    user_answer = parts[1].strip().upper()

    correct = chatbot.student.correct_answer.upper()

    chatbot.student.questions_answered += 1

    chatbot.student.quiz_active = False

    if user_answer == correct:

        chatbot.student.quiz_score += 1
        chatbot.student.save()

        return f"""
✅ Correct!

Explanation:

{chatbot.student.explanation}\n
Use /score to view your quiz statistics.
"""

    else:

        chatbot.student.save()

        return f"""
❌ Incorrect.

Correct Answer: {correct}

Explanation:

{chatbot.student.explanation}\n
Use /score to view your quiz statistics.
"""

def progress_command(chatbot):

    if chatbot.student.current_course is None:
        return "No active course."

    return f"""
========== Progress ==========

Course : {chatbot.student.current_course.title()}

Current Lesson : {chatbot.student.current_lesson}

Completed Lessons : {len(chatbot.student.completed_lessons)}

Quiz Score : {chatbot.student.quiz_score}

==============================
"""

def next_command(chatbot):
    if chatbot.student.current_lesson > len(chatbot.student.course_outline):

        return """
🎉 Congratulations!

You completed the course.

Use

/reset

to start another course.
"""
    if chatbot.student.current_course is None:
        return "Start a course first using /learn <topic>."

    lesson_number = chatbot.student.current_lesson
    topic = chatbot.student.current_course

    lesson_title = chatbot.student.course_outline[
    lesson_number - 1
    ]

    prompt = f"""
You are an expert teacher.

Teach ONLY this lesson.

Course:
{topic}

Lesson {lesson_number}:
{lesson_title}

Requirements:

- Start with the lesson title.
- Give a simple explanation.
- Give one real-world example.
- Give one practical exercise.
- Use beginner-friendly language.
- Do NOT teach future lessons.
- Do NOT ask follow-up questions.
- Do NOT ask the student anything.
- Do NOT end with a question.
- End immediately after the exercise.
"""

    answer = chatbot.ask(prompt)

    chatbot.student.completed_lessons.append(lesson_title)
    chatbot.student.completed_lesson_contents.append(answer)
    chatbot.student.current_lesson += 1
    chatbot.student.save()

    return answer

def reset_command(chatbot):

    chatbot.reset()
    chatbot.student.reset_course()

    return """
Learning progress has been reset.

Conversation history cleared.
Course removed.
Progress reset.

Start a new course using:

/learn <topic>
"""

def course_command(chatbot):

    if chatbot.student.current_course is None:
        return "No active course."

    output = ""

    output += "==================================\n"
    output += f"Course: {chatbot.student.current_course.title()}\n"
    output += "==================================\n\n"

    # <-- Step 3 goes here
    for index, lesson in enumerate(chatbot.student.course_outline, start=1):

        if index < chatbot.student.current_lesson:
            symbol = "✓"

        elif index == chatbot.student.current_lesson:
            symbol = "▶"

        else:
            symbol = "□"

        output += f"{symbol} Lesson {index}\n  {lesson}\n\n"

    total_lessons = len(chatbot.student.course_outline)

    completed = chatbot.student.current_lesson - 1

    percentage = int((completed / total_lessons) * 100)

    output += "==================================\n\n"

    output += f"Progress: {completed} / {total_lessons} Lessons Completed ({percentage}%)\n\n"

    if chatbot.student.current_lesson > total_lessons:
        output += "Current Lesson: Course Completed 🎉\n\n"
        output += "Start another course using:\n\n/learn <topic>\n\n"
    else:
        output += f"Current Lesson: {chatbot.student.current_lesson}\n\n"

    output += "=================================="

    return output

def review_command(chatbot, command):

    if chatbot.student.current_course is None:
        return "Start a course first using /learn <topic>."

    if not chatbot.student.completed_lessons:
        return "You have not completed any lessons yet."

    parts = command.split()

    if len(parts) == 1:

        review = """
========== Completed Lessons ==========

"""

        for number, lesson in enumerate(
            chatbot.student.completed_lessons, start=1
        ):
            review += f"{number}. {lesson}\n"

        review += """
========================================

Use /review <number> to review a lesson.
"""

        return review

    try:
        lesson_number = int(parts[1])
    except ValueError:
        return "Usage: /review <number>"

    if lesson_number < 1 or lesson_number > len(
        chatbot.student.completed_lessons
    ):
        return "Invalid lesson number."

    lesson_title = chatbot.student.completed_lessons[
        lesson_number - 1
    ]

    lesson_content = chatbot.student.completed_lesson_contents[
    lesson_number - 1
    ]

    topic = chatbot.student.current_course

    prompt = f"""
You are an expert teacher helping a beginner review a completed lesson.

Course:
{topic}

Lesson Title:
{lesson_title}

Lesson Content:
{lesson_content}

Create a concise review based ONLY on the lesson content provided above.

Rules:
- Do not use outside knowledge.
- Do not add facts that are not in the lesson.
- Do not infer new information.
- Keep all explanations consistent with the lesson.
- You may reorganize or simplify the information.
- You may use examples from the lesson.
- Do not teach future lessons.
- Do not ask a follow-up question.

Include:

1. Key concept
2. Simple explanation
3. Important points
4. Practical example
"""

    return chatbot.ask(prompt)

def score_command(chatbot):

    answered = chatbot.student.questions_answered
    correct = chatbot.student.quiz_score
    incorrect = answered - correct

    if answered == 0:
        accuracy = 0
    else:
        accuracy = round((correct / answered) * 100)

    return f"""
========== Quiz Statistics ==========

Questions Answered : {answered}

Correct Answers    : {correct}

Incorrect Answers  : {incorrect}

Accuracy           : {accuracy}%

====================================
"""
def flashcards_command(chatbot):

    if chatbot.student.current_course is None:
        return "Start a course first using /learn <topic>."

    if not chatbot.student.completed_lesson_contents:
        return "Complete a lesson first before using flashcards."

    lesson_index = random.randrange(
        len(chatbot.student.completed_lesson_contents)
    )

    lesson_title = chatbot.student.completed_lessons[
        lesson_index
    ]

    lesson_content = chatbot.student.completed_lesson_contents[
        lesson_index
    ]

    prompt = f"""
You are an expert teacher creating a flashcard for a beginner.

Course:
{chatbot.student.current_course}

Lesson:
{lesson_title}

Lesson Content:
{lesson_content}

Create ONE flashcard based ONLY on the lesson content.

Rules:
- Do not use outside knowledge.
- Do not introduce information not contained in the lesson.
- Keep the question simple and clear.
- The answer must be directly supported by the lesson.

Return EXACTLY this format and nothing else:

Question:
<question>

Answer:
<answer>

Do not include:
- Follow-up questions
- Additional explanations
- Extra sections
- Suggestions
- Text before "Question:"
- Text after the answer
"""

    answer = chatbot.ask(prompt)

    question_start = answer.find("Question:")
    answer_start = answer.find("Answer:")

    if question_start == -1 or answer_start == -1:
        return "Unable to create flashcard. Please try again."

    question = answer[
        question_start + len("Question:"):
        answer_start
    ].strip()

    flashcard_answer = answer[
        answer_start + len("Answer:"):
    ].strip()

    chatbot.student.current_flashcard = question
    chatbot.student.current_flashcard_answer = flashcard_answer
    chatbot.student.flashcard_active = True
    chatbot.student.flashcard_status = None

    chatbot.student.save()

    return f"""
========== Flashcard ==========

Question:

{question}

Type /flip to reveal the answer.

===============================
"""

def flip_command(chatbot):

    if not chatbot.student.flashcard_active:
        return "No active flashcard. Use /flashcards first."

    answer = chatbot.student.current_flashcard_answer

    chatbot.student.flashcard_active = False
    chatbot.student.save()

    return f"""
========== Flashcard Answer ==========

{answer}

======================================
"""

def know_command(chatbot):

    if chatbot.student.flashcard_active:
        return "Flip the flashcard first using /flip."

    if chatbot.student.current_flashcard == "":
        return "No active flashcard. Use /flashcards first."

    chatbot.student.flashcard_status = "known"
    chatbot.student.save()

    return "✅ Marked as known."

def difficult_command(chatbot):

    if chatbot.student.flashcard_active:
        return "Flip the flashcard first using /flip."

    if chatbot.student.current_flashcard == "":
        return "No active flashcard. Use /flashcards first."

    chatbot.student.flashcard_status = "difficult"

    for flashcard in chatbot.student.difficult_flashcards:

        if flashcard["question"] == chatbot.student.current_flashcard:
            chatbot.student.save()
            return "📌 Already marked for review."

    flashcard = {
        "question": chatbot.student.current_flashcard,
        "answer": chatbot.student.current_flashcard_answer
    }

    chatbot.student.difficult_flashcards.append(flashcard)

    chatbot.student.save()

    return "📌 Marked for review."

def review_flashcards_command(chatbot):

    if not chatbot.student.difficult_flashcards:
        return "No difficult flashcards saved."

    chatbot.student.review_flashcard_index = 0

    flashcard = chatbot.student.difficult_flashcards[0]

    chatbot.student.current_flashcard = flashcard["question"]
    chatbot.student.current_flashcard_answer = flashcard["answer"]

    chatbot.student.flashcard_active = True
    chatbot.student.flashcard_status = None

    chatbot.student.save()

    return f"""
========== Flashcard Review ==========

Question:

{flashcard["question"]}

Type /flip to reveal the answer.

======================================
"""

def known_command(chatbot):

    if chatbot.student.flashcard_active:
        return "Flip the flashcard first using /flip."

    if chatbot.student.current_flashcard == "":
        return "No active flashcard. Use /review-flashcards first."

    index = chatbot.student.review_flashcard_index

    if index < 0 or index >= len(chatbot.student.difficult_flashcards):
        return "No active difficult flashcard."

    flashcard = chatbot.student.difficult_flashcards[index]

    if flashcard["question"] != chatbot.student.current_flashcard:
        return "The current flashcard does not match the review card."

    chatbot.student.difficult_flashcards.pop(index)

    chatbot.student.flashcard_status = "known"

    if chatbot.student.difficult_flashcards:

        if index >= len(chatbot.student.difficult_flashcards):
            index = 0

        chatbot.student.review_flashcard_index = index

        next_flashcard = chatbot.student.difficult_flashcards[index]

        chatbot.student.current_flashcard = next_flashcard["question"]
        chatbot.student.current_flashcard_answer = next_flashcard["answer"]

        chatbot.student.flashcard_active = True
        chatbot.student.flashcard_status = None

        chatbot.student.save()

        return f"""
✅ Removed from difficult flashcards.

========== Next Flashcard ==========

Question:

{next_flashcard["question"]}

Type /flip to reveal the answer.

=====================================
"""

    chatbot.student.review_flashcard_index = -1
    chatbot.student.current_flashcard = ""
    chatbot.student.current_flashcard_answer = ""
    chatbot.student.flashcard_active = False

    chatbot.student.save()

    return "✅ Removed from difficult flashcards. You have no more difficult flashcards."

def execute(chatbot, command):

    command = command.lower()

    if command == "/help":
        return help_command(chatbot)

    elif command == "/clear":
        return clear_command(chatbot)

    elif command == "/history":
        return history_command(chatbot)

    elif command == "/model":
        return model_command(chatbot)

    elif command.startswith("/learn"):
        return learn_command(chatbot, command)

    elif command == "/progress":
        return progress_command(chatbot)

    elif command == "/next":
        return next_command(chatbot)

    elif command == "/reset":
        return reset_command(chatbot)
    
    elif command == "/course":
        return course_command(chatbot)

    elif command == "/quiz":
        return quiz_command(chatbot)

    elif command.startswith("/answer"):
        return answer_command(chatbot, command)

    elif command == "/review-flashcards":
         return review_flashcards_command(chatbot)

    elif command.startswith("/review"):
        return review_command(chatbot, command)

    elif command == "/score":
        return score_command(chatbot)

    elif command == "/flashcards":
        return flashcards_command(chatbot)

    elif command == "/flip":
        return flip_command(chatbot)

    elif command == "/know":
        return know_command(chatbot)

    elif command == "/known":
        return known_command(chatbot)

    elif command == "/difficult":
        return difficult_command(chatbot)

    else:
        return "Unknown command. Type /help"