FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip3 install -r requirements.txt

EXPOSE 8080

RUN python3 manage.py collectstatic

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8080"]
