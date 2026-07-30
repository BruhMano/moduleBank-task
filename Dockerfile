FROM python:3.14

WORKDIR /app

COPY Pipfile Pipfile.lock ./

RUN pip install pipenv && pipenv install --system --deploy

COPY /app ./

CMD ["fastapi", "run", "main.py", "--port", "8080"]