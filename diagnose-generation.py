from app.main import build_grounded_prompt, generate_answer, retrieve_chunks

question = "When do backups run?"
matches = retrieve_chunks(question, 5, debug=True)
print(generate_answer(build_grounded_prompt(question, matches)))
