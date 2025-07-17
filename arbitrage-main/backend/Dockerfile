FROM python:3.13.1-slim

WORKDIR /api

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# CMD ["python", "manage.py", "runserver", "127.0.0.1:8000"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]