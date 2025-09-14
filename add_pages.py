from app import db, Page, app

with app.app_context():
    existing_titles = [p.title for p in Page.query.all()]

    pages_to_add = [
        Page(
            title="Welcome Page",
            content="This is the first page! Solve the challenge to get your unlock code.",
            unlock_code="WELCOME123",
            unlock_type="quiz",
            question="What is 2 + 2?",
            answer="4"
        ),
        Page(
            title="Debug Page",
            content="Fix the code to unlock the next page.",
            unlock_code="DEBUG1",
            unlock_type="quiz",
            question="Fix this Python: print('Hello' + 5)",
            answer="print('Hello' + str(5))"
        ),
        Page(
            title="Final Challenge",
            content="Solve this final puzzle to complete the CTF!",
            unlock_code="FINAL999",
            unlock_type="quiz",
            question="What is the output of 3*3?",
            answer="9"
        )
    ]

    for page in pages_to_add:
        if page.title not in existing_titles:
            db.session.add(page)
            print(f"Adding page: {page.title}")
        else:
            print(f"Page already exists: {page.title}")

    db.session.commit()
    print("All pages added successfully!")
