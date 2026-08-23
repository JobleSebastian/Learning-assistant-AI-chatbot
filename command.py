from prompts import QUIZ_PROMPT, QUALITY_CHECK_PROMPT, LESSON_PROMPT, LEARNING_POINT_PROMPT
import random
import string
import time
import re

print(">>> LOADED extract_learning_points FROM:", __file__)

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

    chatbot.student.reset_course()

    chatbot.student.current_course = topic
    chatbot.student.course_outline = parse_outline(outline)
    chatbot.student.current_lesson = 1

    chatbot.student.save()
        

    return f"""
Course created!

Topic:
{topic.title()}

Course Outline

{outline}

Type /next to begin.
"""

def normalize_question(question):

    question = question.lower().strip()

    question = question.translate(
        str.maketrans("", "", string.punctuation)
    )

    question = " ".join(question.split())

    return question

def normalize_learning_point(text):
    text = text.lower().strip()

    text = text.translate(
        str.maketrans("", "", string.punctuation)
    )

    text = " ".join(text.split())

    return text

def extract_learning_points(chatbot, topic, lesson_title, lesson_content):

    prompt = LEARNING_POINT_PROMPT.format(
        topic=topic,
        lesson_title=lesson_title,
        lesson_content=lesson_content
    )

    answer = chatbot.ask_once(prompt)

    learning_points = []

    lines = answer.splitlines()

    for i, line in enumerate(lines):

        line = line.strip()

        if line.startswith("Learning Point") and ":" in line:

            if i + 1 < len(lines):

                point = lines[i + 1].strip()

                if point:
                    learning_points.append(point)

    return learning_points

def test_learning_point_extraction(chatbot):

    lesson_title = chatbot.student.completed_lessons[1]

    lesson_index = chatbot.student.completed_lessons.index(
        lesson_title
    )

    lesson_content = chatbot.student.completed_lesson_contents[
        lesson_index
    ]

    points = extract_learning_points(
        chatbot,
        chatbot.student.current_course,
        lesson_title,
        lesson_content
    )

    print("\n========== LEARNING POINT TEST ==========")
    print("Lesson:", lesson_title)
    print("Number of points:", len(points))

    for i, point in enumerate(points, 1):
        print(f"{i}. {point}")

    print("=========================================")

def is_duplicate_quiz(
    chatbot,
    question,
    lesson_title,
    learning_point=None
):

    normalized_question = normalize_question(question)

    for item in chatbot.student.quiz_history:

        if not isinstance(item, dict):
            continue

        if item.get("lesson") != lesson_title:
            continue

        previous_question = item.get("question", "")
        previous_learning_point = item.get(
            "learning_point",
            ""
        )

        # Question duplicate
        if previous_question:

            if normalized_question == normalize_question(
                previous_question
            ):
                print(
                    "DUPLICATE REASON: "
                    "EXACT QUESTION"
                )
                print(
                    "CURRENT:",
                    question
                )
                print(
                    "PREVIOUS:",
                    previous_question
                )
                return True

        # Learning-point duplicate
        if learning_point and previous_learning_point:

            current_lp = normalize_learning_point(
                learning_point
            )

            previous_lp = normalize_learning_point(
                previous_learning_point
            )

            if current_lp == previous_lp:
                print("DUPLICATE REASON: EXACT LEARNING POINT")
                return True

            # Detect same concept with different wording
            current_words = set(current_lp.split())
            previous_words = set(previous_lp.split())

            common_words = (
                current_words.intersection(previous_words)
            )

            if len(common_words) >= 3:

                print(
                    "DUPLICATE REASON: "
                    "SIMILAR LEARNING POINT"
                )
                print(
                    "CURRENT LP:",
                    learning_point
                )
                print(
                    "PREVIOUS LP:",
                    previous_learning_point
                )

                return True

    return False

def extract_quiz_question_text(answer):

    correct_start = answer.find("Correct Answer:")

    if correct_start == -1:
        return ""

    question_part = answer[:correct_start].strip()

    if not question_part.startswith("Question:"):
        return ""

    question_part = question_part[
        len("Question:"):
    ].strip()

    lines = []

    for line in question_part.splitlines():

        line = line.strip()

        if line.startswith(("A.", "B.", "C.", "D.")):
            continue

        if line:
            lines.append(line)

    return " ".join(lines).strip()

def extract_quiz_question(answer):

    correct_start = answer.find("Correct Answer:")

    if correct_start == -1:
        return ""

    question_part = answer[:correct_start].strip()

    if not question_part.startswith("Question:"):
        return ""

    return question_part

def validate_quiz_semantics(chatbot, answer, lesson_content):
    prompt = f"""
You are validating a multiple-choice quiz question.

Lesson Content:
{lesson_content}

Quiz:
{answer}

Determine whether the quiz is logically valid according to ONLY
the lesson content.

Requirements:
- Exactly one option must be supported as correct.
- The stated correct answer must actually be correct.
- No other option may also be independently correct.
- Do not use outside knowledge.
- Ignore whether the formatting is correct.

Return EXACTLY one word:

VALID

or

INVALID
"""

    result = chatbot.ask(prompt)

    return result.strip().upper() == "VALID"

def validate_quiz(answer):

    correct_start = answer.find("Correct Answer:")
    learning_start = answer.find("Learning Point:")
    explanation_start = answer.find("Explanation:")

    if correct_start == -1:
        return False

    if learning_start == -1:
        return False

    if explanation_start == -1:
        return False

    # Correct Answer must be between Correct Answer and Learning Point
    correct = answer[
        correct_start + len("Correct Answer:"):
        learning_start
    ].strip()

    if correct not in ["A", "B", "C", "D"]:
        return False

    # Learning Point must contain something
    learning_point = answer[
        learning_start + len("Learning Point:"):
        explanation_start
    ].strip()

    if not learning_point:
        return False

    # Explanation must contain something
    explanation = answer[
        explanation_start + len("Explanation:"):
    ].strip()

    if not explanation:
        return False

    return True

MAX_QUESTIONS_PER_LESSON = 5

def choose_quiz_lesson(chatbot):

    lessons = chatbot.student.completed_lessons

    if not lessons:
        return None

    lesson_counts = {
        lesson: get_lesson_quiz_count(
            chatbot,
            lesson
        )
        for lesson in lessons
    }

    available_lessons = [
        lesson
        for lesson in lessons
        if lesson_counts[lesson] < MAX_QUESTIONS_PER_LESSON
    ]

    if not available_lessons:
        return None

    if (
        len(available_lessons) > 1
        and chatbot.student.last_quiz_lesson in available_lessons
    ):
        available_lessons.remove(
            chatbot.student.last_quiz_lesson
        )

    return random.choice(available_lessons)

def get_lesson_quiz_count(chatbot, lesson_title):

    count = 0

    for item in chatbot.student.quiz_history:

        if isinstance(item, dict):
            if item.get("lesson") == lesson_title:
                count += 1

    return count

def get_lesson_learning_points(lesson_title):

    if lesson_title == "Identify bike components: pedals, handlebars, brakes, gears":
        return [
            "pedals",
            "handlebars",
            "brakes",
            "gears"
        ]

    elif lesson_title == "Balance without moving using feet on the ground":
        return [
            "feet on ground",
            "body centered",
            "weight adjustment",
            "relaxed hands",
            "upright posture"
        ]

    elif lesson_title == "Push off and pedal smoothly to move forward":
        return [
            "push off",
            "placing foot on pedal",
            "relaxed legs",
            "circular pedaling",
            "steady rhythm",
            "upright body"
        ]

    elif lesson_title == "Practice steering by turning handlebars gently":
        return [
            "handlebar direction",
            "gentle handlebar movement",
            "centered body",
            "avoid jerking",
            "smooth movements",
            "look ahead"
        ]

    elif lesson_title == "Learn to apply brakes safely without skidding":
        return [
            "gradual braking",
            "even brake pressure",
            "front brake",
            "rear brake",
            "body centered",
            "avoid sudden braking",
            "look ahead"
        ]

    return []

def clean_quiz_format(text):

    text = text.replace("**", "")

    text = re.sub(
        r"^\s*Options:\s*$",
        "",
        text,
        flags=re.MULTILINE | re.IGNORECASE
    )

    text = re.sub(
        r"^\s*Answer:\s*",
        "Correct Answer: ",
        text,
        flags=re.MULTILINE | re.IGNORECASE
    )

    return text.strip()

def quiz_command(chatbot):

    if chatbot.student.quiz_active:
        return (
            "You already have an active quiz. "
            "Answer it before starting another quiz."
        )

    if chatbot.student.current_course is None:
        return "Start a course first using /learn <topic>."

    if chatbot.student.current_lesson == 1:
        return "Complete the first lesson before taking a quiz."

    lesson_title = choose_quiz_lesson(chatbot)

    if lesson_title is None:
        return (
            "All completed lessons have reached "
            f"{MAX_QUESTIONS_PER_LESSON} quiz questions."
        )

    lesson_index = chatbot.student.completed_lessons.index(
        lesson_title
    )

    lesson_content = chatbot.student.completed_lesson_contents[
        lesson_index
    ]

    # Extract all meaningful learning points for this lesson
    learning_points = chatbot.student.lesson_learning_points.get(
        lesson_title
    )

    if not learning_points:

        learning_points = chatbot.student.lesson_learning_points.get(
            lesson_title,
            []
        )

        chatbot.student.lesson_learning_points[
            lesson_title
        ] = learning_points

        chatbot.student.save()

    # Hard maximum of 5 quiz questions per lesson
    learning_points = learning_points[:5]

    # Find learning points that have already been tested
    tested_learning_points = []

    for item in chatbot.student.quiz_history:

        if not isinstance(item, dict):
            continue

        if item.get("lesson") != lesson_title:
            continue

        learning_point = item.get(
            "learning_point",
            ""
        ).strip()

        if learning_point:
            tested_learning_points.append(
                normalize_learning_point(learning_point)
            )

    # Keep only learning points that have NOT been tested
    remaining_learning_points = []

    for point in learning_points:

        if normalize_learning_point(point) not in tested_learning_points:
            remaining_learning_points.append(point)

    # No unused learning points remain
    if not remaining_learning_points:
        return (
            "All meaningful learning points in this lesson "
            "have already been quizzed."
        )

    # Select exactly ONE learning point for this quiz
    target_learning_point = remaining_learning_points[0]

    # Give the model ONLY this learning point
    history_text = f"""
    The ONLY learning point you may test is:

    {target_learning_point}

    You MUST test this exact learning point.
    Do not choose a different learning point.
    Do not broaden, narrow, or substitute it.
    """

    base_prompt = QUIZ_PROMPT.format(
        topic=chatbot.student.current_course,
        lesson_title=lesson_title,
        lesson_content=lesson_content,
        quiz_history=history_text
    )

    prompt = base_prompt

    MAX_QUIZ_RETRIES = 2

    for attempt in range(MAX_QUIZ_RETRIES):

        answer = chatbot.ask_once(prompt)

        answer = clean_quiz_format(answer)

        valid = validate_quiz(answer)

        if not valid:

            if attempt == MAX_QUIZ_RETRIES - 1:
                return (
                    "Quiz generation failed after "
                    f"{MAX_QUIZ_RETRIES} attempts. "
                    "Please use /quiz again."
                )

            prompt = base_prompt + """

IMPORTANT:

The previous response did not follow the required output format.

Generate exactly ONE multiple-choice question.

Use exactly this structure:

Question:
<question>

A. <option>
B. <option>
C. <option>
D. <option>

Correct Answer: <A/B/C/D>

Explanation:
<1-2 sentences>

Correct Answer must contain ONLY one letter.
Do not include Learning Point, Answer, Options, Rationale,
Follow-up question, or any other text.
"""

            continue

        question = extract_quiz_question(answer)
        question_text = extract_quiz_question_text(answer)

        learning_start = answer.find("Learning Point:")
        explanation_start = answer.find("Explanation:")

        if learning_start == -1 or explanation_start == -1:
            if attempt == MAX_QUIZ_RETRIES - 1:
                return (
                    "Quiz generation failed after "
                    f"{MAX_QUIZ_RETRIES} attempts. "
                    "Please use /quiz again."
                )

            prompt = base_prompt + """

        IMPORTANT:

        The previous response did not follow the required output format.

        Generate exactly ONE multiple-choice question.

        Use exactly this structure:

        Question:
        <question>

        A. <option>
        B. <option>
        C. <option>
        D. <option>

        Correct Answer: <A/B/C/D>

        Learning Point:
        <one short learning point>

        Explanation:
        <1-2 sentences>

        Correct Answer must contain ONLY one letter.
        Do not include Answer, Options, Rationale,
        Follow-up question, or any other text.
        """

            continue

        learning_point = answer[
            learning_start + len("Learning Point:"):
            explanation_start
        ].strip()

        break

    chatbot.student.last_quiz_lesson = lesson_title
    chatbot.student.current_quiz_lesson = lesson_title

    correct_start = answer.find("Correct Answer:")
    learning_start = answer.find("Learning Point:")
    explanation_start = answer.find("Explanation:")

    if (
        correct_start == -1
        or learning_start == -1
        or explanation_start == -1
    ):
        return "Quiz generation failed because the answer format was incomplete."

    correct = answer[
        correct_start + len("Correct Answer:"):
        learning_start
    ].strip()

    explanation = answer[
        explanation_start + len("Explanation:")
    :].strip()

    chatbot.student.correct_answer = correct.upper()
    chatbot.student.explanation = explanation

    chatbot.student.current_question = answer
    chatbot.student.quiz_active = True

    chatbot.student.quiz_history.append({
        "question": question_text,
        "lesson": lesson_title,
        "correct_answer": correct.upper(),
        "learning_point": learning_point
    })

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
    is_correct = user_answer == correct

    chatbot.student.questions_answered += 1

    chatbot.student.quiz_results.append({
        "question": chatbot.student.current_question,
        "lesson": chatbot.student.current_quiz_lesson,
        "correct": is_correct
    })

    chatbot.student.quiz_active = False

    if is_correct:

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

    total_lessons = len(chatbot.student.course_outline)
    completed_lessons = len(chatbot.student.completed_lessons)

    if total_lessons > 0:
        progress = (completed_lessons / total_lessons) * 100
    else:
        progress = 0

    if completed_lessons >= total_lessons and total_lessons > 0:
        status = "Course Completed!"

        return f"""
========== Progress ==========

Course : {chatbot.student.current_course.title()}

Completed Lessons : {completed_lessons} / {total_lessons}

Progress : {progress:.0f}%

Status : {status}

Quiz Score : {chatbot.student.quiz_score}

==============================
"""

    return f"""
========== Progress ==========

Course : {chatbot.student.current_course.title()}

Completed Lessons : {completed_lessons} / {total_lessons}

Current Lesson : {chatbot.student.current_lesson}

Progress : {progress:.0f}%

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

    if chatbot.student.current_course is None:
        return "Start a course first using /learn <topic>."

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

            learning_points = extract_learning_points(
                chatbot,
                topic,
                lesson_title,
                answer
            )

            # Maximum of 5 quiz questions per lesson
            learning_points = learning_points[:5]

            chatbot.student.completed_lessons.append(
                lesson_title
            )

            chatbot.student.completed_lesson_contents.append(
                answer
            )

            chatbot.student.lesson_learning_points[
                lesson_title
            ] = learning_points

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

    result = f"""
========== Quiz Statistics ==========

Questions Answered : {answered}

Correct Answers    : {correct}

Incorrect Answers  : {incorrect}

Accuracy           : {accuracy}%
"""

    if chatbot.student.quiz_results:

        lesson_stats = {}

        for item in chatbot.student.quiz_results:

            lesson = item["lesson"]

            if lesson not in lesson_stats:
                lesson_stats[lesson] = {
                    "answered": 0,
                    "correct": 0
                }

            lesson_stats[lesson]["answered"] += 1

            if item["correct"]:
                lesson_stats[lesson]["correct"] += 1

        result += "\n---------- By Lesson ----------\n"

        for lesson, stats in lesson_stats.items():

            lesson_answered = stats["answered"]
            lesson_correct = stats["correct"]

            lesson_accuracy = round(
                (lesson_correct / lesson_answered) * 100
            )

            result += f"""
{lesson}
Questions : {lesson_answered}
Correct   : {lesson_correct}
Accuracy  : {lesson_accuracy}%
"""

    result += """
====================================
"""

    flashcard_results = chatbot.student.flashcard_results

    flashcard_by_lesson = {}

    for item in flashcard_results:

        lesson = item["lesson"]

        if lesson not in flashcard_by_lesson:
            flashcard_by_lesson[lesson] = {
                "cards": 0,
                "known": 0,
                "difficult": 0
            }

        flashcard_by_lesson[lesson]["cards"] += 1

        if item["result"] == "known":
            flashcard_by_lesson[lesson]["known"] += 1

        elif item["result"] == "difficult":
            flashcard_by_lesson[lesson]["difficult"] += 1

    flashcard_section = ""

    current_difficult_questions = {
        flashcard["question"]
        for flashcard in chatbot.student.difficult_flashcards
    }

    if flashcard_by_lesson:

        flashcard_section = """
---------- Flashcard Performance ----------
"""

        for lesson, stats in flashcard_by_lesson.items():

            cards = stats["cards"]
            known = stats["known"]
            difficult = stats["difficult"]

            if cards == 0:
                known_rate = 0
            else:
                known_rate = round((known / cards) * 100)

            current_difficult = len({
                item["question"]
                for item in flashcard_results
                if (
                    item["lesson"] == lesson
                    and item["question"] in current_difficult_questions
                )
            })

            flashcard_section += f"""
{lesson}
Cards Reviewed       : {cards}
Known                : {known}
Difficult            : {difficult}
Currently Difficult  : {current_difficult}
Known Rate           : {known_rate}%
"""

        flashcard_section += """
============================================
"""

    result += flashcard_section

    return result

def get_flashcard_lesson_weights(chatbot):

    weights = []

    for lesson in chatbot.student.completed_lessons:

        # -----------------------------
        # Flashcard performance
        # -----------------------------

        flashcard_results = [
            item
            for item in chatbot.student.flashcard_results
            if item["lesson"] == lesson
        ]

        if not flashcard_results:

            flashcard_weight = 2

        else:

            known = sum(
                1
                for item in flashcard_results
                if item["result"] == "known"
            )

            difficult = sum(
                1
                for item in flashcard_results
                if item["result"] == "difficult"
            )

            total = len(flashcard_results)

            known_rate = known / total

            if known_rate >= 0.75:

                flashcard_weight = 1

            elif known_rate >= 0.50:

                flashcard_weight = 3

            else:

                flashcard_weight = 5

        # -----------------------------
        # Quiz performance
        # -----------------------------

        quiz_results = [
            item
            for item in chatbot.student.quiz_results
            if item["lesson"] == lesson
        ]

        if not quiz_results:

            quiz_weight = 2

        else:

            quiz_correct = sum(
                1
                for item in quiz_results
                if item["correct"]
            )

            quiz_total = len(quiz_results)

            quiz_accuracy = quiz_correct / quiz_total

            if quiz_accuracy >= 0.75:

                quiz_weight = 1

            elif quiz_accuracy >= 0.50:

                quiz_weight = 3

            else:

                quiz_weight = 5

        # -----------------------------
        # Combined lesson difficulty
        # -----------------------------

        weight = flashcard_weight + quiz_weight

        weights.append(weight)

    return weights

def flashcards_command(chatbot):

    if chatbot.student.current_course is None:
        return "Start a course first using /learn <topic>."

    if not chatbot.student.completed_lesson_contents:
        return "Complete a lesson first before using flashcards."

    if chatbot.student.flashcard_active:
        return "Flip the current flashcard first using /flip."

    if chatbot.student.difficult_flashcards:

        review_probability = 0.60

        if random.random() < review_probability:
            return review_flashcards_command(chatbot)

    lesson_weights = get_flashcard_lesson_weights(chatbot)

    lesson_index = random.choices(
        range(len(chatbot.student.completed_lesson_contents)),
        weights=lesson_weights,
        k=1
    )[0]

    lesson_title = chatbot.student.completed_lessons[
        lesson_index
    ]

    lesson_content = chatbot.student.completed_lesson_contents[
        lesson_index
    ]

    recent_flashcard_history = chatbot.student.flashcard_history[-5:]

    history_text = ""

    for item in recent_flashcard_history:
        history_text += (
            f"- Question: {item['question']}\n"
            f"  Lesson: {item['lesson']}\n"
        )

    prompt = f"""
You are an expert teacher creating a flashcard for a beginner.

Course:
{chatbot.student.current_course}

Lesson:
{lesson_title}

Lesson Content:
{lesson_content}

Recent Flashcards:
{history_text}

Create ONE flashcard based ONLY on the lesson content.

Rules:
- Do not use outside knowledge.
- Do not introduce information not contained in the lesson.
- Keep the question simple and clear.
- The answer must be directly supported by the lesson.
- Do not repeat or closely rephrase any previous flashcard question.
- Prioritize the lesson's main concept, rule, definition, process, or technique.
- Prefer an important learning point that has not recently been tested when one is available.
- Do not use a real-world example as the flashcard topic when the lesson contains a more important learning point.
- Do not create a flashcard merely to recall an example, analogy, or exercise detail unless it is itself an important learning point.
- Distinguish between instructions for an exercise and instructions for the actual skill being taught.
- Do not generalize a temporary or stationary exercise position into a rule for normal riding.
- Make sure the answer applies directly to the situation described in the question.
- Distinguish between an exercise instruction and the actual skill or concept being taught.
- Do not generalize a temporary condition, exercise setup, or practice instruction into a general rule.
- Make sure the answer applies directly to the situation described in the question.
- Do not turn a detail from an example or exercise into a general rule unless the lesson explicitly presents it as a general rule.

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

    MAX_FLASHCARD_RETRIES = 3

    for attempt in range(MAX_FLASHCARD_RETRIES):

        answer = chatbot.ask(prompt)

        if not validate_flashcard(answer):

            if attempt == MAX_FLASHCARD_RETRIES - 1:
                return (
                    "Flashcard generation failed after "
                    f"{MAX_FLASHCARD_RETRIES} attempts. "
                    "Please use /flashcards again."
                )

            continue

        question_start = answer.find("Question:")
        answer_start = answer.find("Answer:")

        question = answer[
            question_start + len("Question:"):
            answer_start
        ].strip()

        flashcard_answer = answer[
            answer_start + len("Answer:"):
        ].strip()

        if is_duplicate_flashcard(
            chatbot,
            question,
            lesson_title
        ):

            prompt += f"""

IMPORTANT:
The generated question below was rejected because it is too similar
to a previous flashcard:

Rejected question:
{question}

Generate a DIFFERENT question that tests another important concept
from the lesson.

Do not repeat or closely rephrase the rejected question.
Do not test the same learning point using different wording.
Choose a different learning point from the lesson if one is available.
"""

            if attempt == MAX_FLASHCARD_RETRIES - 1:
                return (
                    "Flashcard generation failed because "
                    "a unique question could not be created. "
                    "Please use /flashcards again."
                )

            continue

        if is_poor_flashcard(question, flashcard_answer):

            prompt += """

IMPORTANT:
The generated flashcard has a poor question-answer relationship.
The question gives away too much of the answer or is too similar
to the answer itself.

Generate a clearer question that tests the learning point without
repeating the answer in the question.

Do not change the underlying learning point.
"""

            if attempt == MAX_FLASHCARD_RETRIES - 1:
                return (
                    "Flashcard generation failed because "
                    "a high-quality question could not be created. "
                    "Please use /flashcards again."
                )

            continue

        break

    chatbot.student.current_flashcard = question
    chatbot.student.current_flashcard_answer = flashcard_answer
    chatbot.student.current_flashcard_lesson = lesson_title
    chatbot.student.flashcard_active = True
    chatbot.student.flashcard_status = None

    chatbot.student.flashcard_history.append({
        "question": question,
        "lesson": lesson_title
    })

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
    chatbot.student.flashcard_results.append({
        "question": chatbot.student.current_flashcard,
        "lesson": chatbot.student.current_flashcard_lesson,
        "result": "known"
    })
    chatbot.student.save()

    return "✅ Marked as known."

def difficult_command(chatbot):

    if chatbot.student.flashcard_active:
        return "Flip the flashcard first using /flip."

    if chatbot.student.current_flashcard == "":
        return "No active flashcard. Use /flashcards first."

    for flashcard in chatbot.student.difficult_flashcards:

        if flashcard["question"] == chatbot.student.current_flashcard:
            chatbot.student.save()
            return "📌 Already marked for review."

    chatbot.student.flashcard_status = "difficult"
    chatbot.student.flashcard_results.append({
        "question": chatbot.student.current_flashcard,
        "lesson": chatbot.student.current_flashcard_lesson,
        "result": "difficult"
    })

    flashcard = {
        "question": chatbot.student.current_flashcard,
        "answer": chatbot.student.current_flashcard_answer,
        "lesson": chatbot.student.current_flashcard_lesson
    }

    chatbot.student.difficult_flashcards.append(flashcard)

    chatbot.student.save()

    return "📌 Marked for review."

COMMON_QUESTION_WORDS = {
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "how",
    "is",
    "are",
    "was",
    "were",
    "do",
    "does",
    "did",
    "should",
    "can",
    "could",
    "would",
    "the",
    "a",
    "an",
    "of",
    "to",
    "in",
    "for",
    "on",
    "your",
    "you"
}

def are_similar_questions(question1, question2):

    normalized1 = normalize_question(question1)
    normalized2 = normalize_question(question2)

    # Exact normalized match
    if normalized1 == normalized2:
        return True

    words1 = set(normalized1.split())
    words2 = set(normalized2.split())

    words1 -= COMMON_QUESTION_WORDS
    words2 -= COMMON_QUESTION_WORDS

    if not words1 or not words2:
        return False

    # Strong word overlap
    common_words = words1.intersection(words2)
    total_words = words1.union(words2)

    similarity = len(common_words) / len(total_words)

    if similarity >= 0.80:
        return True

    # Important learning-point keywords
    learning_points = [
        {
            "name": "steering",
            "keywords": {
                "steer",
                "steering",
                "handlebars",
                "turning",
                "turn"
            }
        },
        {
            "name": "braking",
            "keywords": {
                "brake",
                "brakes",
                "braking",
                "stopping",
                "stop",
                "skidding"
            }
        },
        {
            "name": "balance",
            "keywords": {
                "balance",
                "balancing",
                "stable",
                "stability",
                "centered"
            }
        },
        {
            "name": "pedaling",
            "keywords": {
                "pedal",
                "pedaling",
                "pedals",
                "rhythm",
                "circular"
            }
        },
        {
            "name": "starting",
            "keywords": {
                "start",
                "starting",
                "push",
                "push-off",
                "move"
            }
        }
    ]

    for point in learning_points:

        keywords = point["keywords"]

        matches1 = words1.intersection(keywords)
        matches2 = words2.intersection(keywords)

        if matches1 and matches2:
            return True

    return False

def is_duplicate_flashcard(chatbot, question, lesson_title):

    for item in chatbot.student.flashcard_history:

        if item["lesson"] != lesson_title:
            continue

        previous_question = item["question"]

        if normalize_question(question) == normalize_question(
            previous_question
        ):
            return True

        if are_similar_questions(
            question,
            previous_question
        ):
            return True

    return False

def is_semantic_duplicate(chatbot, question, lesson_title):

    previous_questions = [
        item["question"]
        for item in chatbot.student.flashcard_history
        if item["lesson"] == lesson_title
    ]

    if not previous_questions:
        return False

    history_text = ""

    for previous_question in previous_questions:
        history_text += f"- {previous_question}\n"

    prompt = f"""
You are checking whether a newly generated flashcard
tests the same learning concept as any previous flashcard.

New Question:
{question}

Previous Flashcard Questions:
{history_text}

Determine whether the new question tests essentially the
same learning concept as any previous question.

Examples:

"Why is footwork important in batting?"
"What is the purpose of footwork in batting?"
=> DUPLICATE

"When should you use a lower gear?"
"What should you do when riding on rough terrain?"
=> DUPLICATE if they test the same gear-selection concept.

"What should you do to maintain steady control while avoiding obstacles?"
"What should you do to stay focused while avoiding obstacles?"
=> NOT DUPLICATE if they test different learning points.

Return EXACTLY one word:

DUPLICATE

or

UNIQUE

Do not provide an explanation.
"""

    result = chatbot.ask(prompt)

    return result.strip().upper().startswith("DUPLICATE")

def is_poor_flashcard(question, answer):

    normalized_question = normalize_question(question)
    normalized_answer = normalize_question(answer)

    if normalized_question == normalized_answer:
        return True

    question_words = set(normalized_question.split())
    answer_words = set(normalized_answer.split())

    if not question_words or not answer_words:
        return False

    overlap = len(
        question_words.intersection(answer_words)
    ) / len(question_words)

    if overlap >= 0.70:
        return True

    return False

def validate_flashcard(answer):

    question_start = answer.find("Question:")
    answer_start = answer.find("Answer:")

    if question_start == -1:
        return False

    if answer_start == -1:
        return False

    question = answer[
        question_start + len("Question:"):
        answer_start
    ].strip()

    flashcard_answer = answer[
        answer_start + len("Answer:"):
    ].strip()

    if not question:
        return False

    if not flashcard_answer:
        return False

    if "Follow-up question:" in flashcard_answer:
        return False

    if "Follow-up:" in flashcard_answer:
        return False

    return True

def review_flashcards_command(chatbot):

    if not chatbot.student.difficult_flashcards:
        return "No difficult flashcards saved."

    chatbot.student.review_flashcard_index = 0

    flashcard = chatbot.student.difficult_flashcards[0]

    chatbot.student.current_flashcard = flashcard["question"]
    chatbot.student.current_flashcard_answer = flashcard["answer"]
    chatbot.student.current_flashcard_lesson = flashcard["lesson"]

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

    chatbot.student.flashcard_results.append({
        "question": flashcard["question"],
        "lesson": flashcard["lesson"],
        "result": "known"
    })

    chatbot.student.flashcard_status = "known"

    if chatbot.student.difficult_flashcards:

        if index >= len(chatbot.student.difficult_flashcards):
            index = 0

        chatbot.student.review_flashcard_index = index

        next_flashcard = chatbot.student.difficult_flashcards[index]

        chatbot.student.current_flashcard = next_flashcard["question"]
        chatbot.student.current_flashcard_answer = next_flashcard["answer"]
        chatbot.student.current_flashcard_lesson = next_flashcard["lesson"]

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
