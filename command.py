from prompts import QUIZ_PROMPT, QUALITY_CHECK_PROMPT, LESSON_PROMPT
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

def validate_quiz(answer):

    correct_start = answer.find("Correct Answer:")
    explanation_start = answer.find("Explanation:")

    if correct_start == -1: 
        return False

    if explanation_start == -1:  
        return False

    question_part = answer[:correct_start].strip()

    correct_part = answer[
        correct_start + len("Correct Answer:"):
        explanation_start
    ].strip()

    explanation = answer.split(
        "Explanation:",
        1
    )[1].strip()

    if not question_part:  
        return False

    if not explanation:   
        return False

    if correct_part.upper() not in ["A", "B", "C", "D"]:    
        return False

    lines = question_part.splitlines()

    options = {}

    for line in lines:

        line = line.strip()

        if line.startswith("A."):
            options["A"] = line[2:].strip()

        elif line.startswith("B."):
            options["B"] = line[2:].strip()

        elif line.startswith("C."):
            options["C"] = line[2:].strip()

        elif line.startswith("D."):
            options["D"] = line[2:].strip()

    

    if len(options) != 4:  
        return False

    for option in ["A", "B", "C", "D"]:

        if not options[option]:      
            return False

    if "Follow-up question:" in explanation:     
        return False

    if "Follow-up:" in explanation:
        return False
    
    return True

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

    recent_quiz_history = chatbot.student.quiz_history[-5:]

    history_text = ""

    for item in recent_quiz_history:
        history_text += f"- {item}\n"        


    prompt = QUIZ_PROMPT.format(
        topic=chatbot.student.current_course,
        lesson_title=lesson_title,
        lesson_content=lesson_content,
        quiz_history=history_text
    )

    MAX_QUIZ_RETRIES = 3

    for attempt in range(MAX_QUIZ_RETRIES):

        answer = chatbot.ask(prompt)


        if validate_quiz(answer):
            break

        if attempt == MAX_QUIZ_RETRIES - 1:
            return (
                "Quiz generation failed after "
                f"{MAX_QUIZ_RETRIES} attempts. "
                "Please use /quiz again."
            )

    chatbot.student.last_quiz_lesson = lesson_title

    correct_start = answer.find("Correct Answer:")
    explanation_start = answer.find("Explanation:")

    correct = answer[
        correct_start + len("Correct Answer:"):
        explanation_start
    ].strip()

    explanation = answer.split(
        "Explanation:",
        1
    )[1].strip()

    chatbot.student.correct_answer = correct.upper()
    chatbot.student.explanation = explanation

    chatbot.student.current_question = answer
    chatbot.student.quiz_active = True
    
    question = answer[:correct_start].strip()

    chatbot.student.quiz_history.append(question)
    chatbot.student.save()

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

def validate_lesson(answer, lesson_number, lesson_title):

    if not answer or not answer.strip():
        return False

    answer_lower = answer.lower()

    # Lesson title must be present
    expected_title = f"Lesson {lesson_number}: {lesson_title}"

    if expected_title.lower() not in answer_lower:
        return False

    # Required sections
    if "example" not in answer_lower:
        return False

    if "exercise" not in answer_lower:
        return False

    # Must not contain follow-up questions
    forbidden_phrases = [
        "follow-up question:",
        "follow up question:",
        "would you like",
        "do you want to",
        "can you think"
    ]

    for phrase in forbidden_phrases:
        if phrase in answer_lower:
            return False

    return True

def next_command(chatbot):

    if chatbot.student.current_lesson > len(
        chatbot.student.course_outline
    ):
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

    prompt = LESSON_PROMPT.format(
        topic=topic,
        lesson_number=lesson_number,
        lesson_title=lesson_title
    )

    subject_guidance = get_subject_guidance(topic)

    if subject_guidance:
        prompt += "\n" + subject_guidance

    MAX_LESSON_RETRIES = 3

    previous_warning = ""

    for attempt in range(MAX_LESSON_RETRIES):

        current_prompt = prompt

        if previous_warning:
            current_prompt = f"""
    {prompt}

    IMPORTANT:
    A previous version of this lesson failed the quality check.

    The reviewer identified this problem:

    {previous_warning}

    Generate a new version that corrects this problem.
    Do not repeat the problematic claim or instruction.
    """
        
        answer = chatbot.ask(current_prompt)

        if not validate_lesson(
            answer,
            lesson_number,
            lesson_title
        ):
            if attempt < MAX_LESSON_RETRIES - 1:
                previous_warning = (
                    "The lesson failed the required lesson structure. "
                    "Make sure it contains the lesson title, an example, "
                    "and a practical exercise."
                )
                continue

            return (
                "Lesson generation failed after "
                f"{MAX_LESSON_RETRIES} attempts. "
                "Please use /next again."
            )

        quality_prompt = QUALITY_CHECK_PROMPT.format(
            topic=topic,
            lesson_title=lesson_title,
            lesson_content=answer
        )

        quality_result = chatbot.ask(quality_prompt)

        if quality_result.strip().upper().startswith("PASS"):

            chatbot.student.completed_lessons.append(
                lesson_title
            )

            chatbot.student.completed_lesson_contents.append(
                answer
            )

            chatbot.student.current_lesson += 1
            chatbot.student.save()

            return answer

        previous_warning = quality_result

        if attempt < MAX_LESSON_RETRIES - 1:
            continue

        return f"""
    Lesson quality check failed after {MAX_LESSON_RETRIES} attempts.

    {quality_result}

    Please use /next again.
    """

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

def dashboard_command(chatbot):

    if chatbot.student.current_course is None:
        return "Start a course first using /learn <topic>."

    total_lessons = len(chatbot.student.course_outline)
    completed_lessons = len(chatbot.student.completed_lessons)

    if total_lessons > 0:
        progress_percent = round(
        (completed_lessons / total_lessons) * 100
    )
    else:
        progress_percent = 0

    bar_length = 10
    filled = round(
          (completed_lessons / total_lessons) * bar_length
    ) if total_lessons > 0 else 0

    progress_bar = "█" * filled + "░" * (bar_length - filled)

    questions_answered = chatbot.student.questions_answered
    quiz_score = chatbot.student.quiz_score

    if questions_answered > 0:
        accuracy = round(
            (quiz_score / questions_answered) * 100
        )
    else:
        accuracy = 0

    difficult_cards = len(
        chatbot.student.difficult_flashcards
    )

    if difficult_cards > 0:
       recommendation = "Review your difficult flashcards using /review-flashcards."

    elif questions_answered > 0 and accuracy < 60:
       recommendation = "Your quiz accuracy is low. Try /review before taking another quiz."

    elif completed_lessons < total_lessons:
       recommendation = "Continue learning with /next."

    else:
       recommendation = "Course completed! Review your knowledge with /quiz."

    return f"""
========== Learning Dashboard ==========

Course:
{chatbot.student.current_course}

Lessons
Progress: {progress_bar} {progress_percent}%
Completed: {completed_lessons} / {total_lessons}
Current Lesson: {chatbot.student.current_lesson}

Quiz
Questions Answered: {questions_answered}
Correct Answers: {quiz_score}
Incorrect Answers: {questions_answered - quiz_score}
Accuracy: {accuracy}%

Flashcards
Difficult Cards: {difficult_cards}

Recommendation
{recommendation}

=========================================
"""

def test_quality_check(chatbot, lesson_content, lesson_title):

    prompt = QUALITY_CHECK_PROMPT.format(
        topic=chatbot.student.current_course,
        lesson_title=lesson_title,
        lesson_content=lesson_content
    )

    result = chatbot.ask(prompt)

    print("\n========== QUALITY CHECK ==========")
    print(result)
    print("===================================\n")

    return result

def quality_command(chatbot):

    if chatbot.student.current_course is None:
        return "Start a course first using /learn <topic>."

    if not chatbot.student.completed_lesson_contents:
        return "Complete a lesson first."

    lesson_index = 5

    lesson_title = chatbot.student.completed_lessons[
        lesson_index
    ]

    lesson_content = chatbot.student.completed_lesson_contents[
        lesson_index
    ]

    prompt = QUALITY_CHECK_PROMPT.format(
        topic=chatbot.student.current_course,
        lesson_title=lesson_title,
        lesson_content=lesson_content
    )

    result = chatbot.ask(prompt)

    return f"""
========== Lesson Quality Check ==========

Lesson:
{lesson_title}

Result:
{result}

==========================================
"""

def get_subject_guidance(topic):

    topic_lower = topic.lower()

    if any(word in topic_lower for word in [
        "tennis",
        "table tennis",
        "volleyball",
        "basketball",
        "football",
        "soccer"
    ]):
        return """
Subject-specific guidance:

- Distinguish official rules from optional techniques and strategies.
- Describe techniques according to their standard definitions.
- Do not define a technique solely by which hand is used unless that is part of its standard definition.
- Do not present optional strategies as mandatory rules.
"""

    if any(word in topic_lower for word in [
        "python",
        "c++",
        "java",
        "programming",
        "coding"
    ]):
        return """
Subject-specific guidance:

- Use correct programming terminology.
- Distinguish programming concepts from practical examples.
- Do not present invalid syntax as working code.
- Keep code examples appropriate for the lesson level.
"""

    return ""

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

    elif command == "/dashboard":
        return dashboard_command(chatbot)

    elif command == "/quality":
        return quality_command(chatbot)

    else:
        return "Unknown command. Type /help"
