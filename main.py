import chatbot
print(chatbot.__file__)
from chatbot import LearningChatbot

bot = LearningChatbot()
bot.student.save()

print("=" * 40)
print("📚 AI Learning Assistant")
print("Type 'quit' to exit.")
print("=" * 40)

while True:

    question = input("\nYou: ")

    if question.lower() == "quit":
        print("\nGoodbye!")
        break

    if question.startswith("/"):
     answer = bot.command(question)
    else:
     answer = bot.ask(question)

    print("\nTutor:")
    print(answer)