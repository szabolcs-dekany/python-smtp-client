FROM python:3.10.9
WORKDIR /app
COPY . .
CMD ["python", "main.py"]