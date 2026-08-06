from ollama import chat
from prompts import SYSTEM_PROMPT
from student import Student
from command import execute

class LearningChatbot:

    def __init__(self):

        self.model = "qwen3:8b"
        self.system_prompt = SYSTEM_PROMPT

        self.student = Student()
        self.student.load()

        self.reset()

    def reset(self):
        self.messages = [
            {
                "role": "system",
                "content": self.system_prompt
            }
        ]

    def ask(self, question):

        self.messages.append(
            {
                "role": "user",
                "content": question
            }
        )

        response = chat(
            model=self.model,
            messages=self.messages
        )

        answer = response.message.content

        self.messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

        return answer

    def command(self, command):

        return execute(self, command)

    def generate_outline(self, topic):

        prompt = f"""
    Create a beginner learning roadmap for {topic}.

    Return ONLY a numbered list of 10 lessons.

    Do not explain anything.
    """

        response = chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.message.content