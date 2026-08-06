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
    chatbot.student.save()

    return f"""
Course created!

Topic:
{topic.title()}

Course Outline

{outline}

Type /next to begin.
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

Teach this lesson from a beginner course on {topic}.

Lesson {lesson_number}:
{lesson_title}

Only teach this lesson.

Include:

1. Lesson title

2. Simple explanation

3. Real-world example

4. Small exercise

Do NOT teach future lessons.

Do NOT ask follow-up questions.
"""

    answer = chatbot.ask(prompt)

    chatbot.student.completed_lessons.append(lesson_title)
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

    output += f"Current Lesson: {chatbot.student.current_lesson}\n\n"

    output += "=================================="

    return output

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

    else:
        return "Unknown command. Type /help"