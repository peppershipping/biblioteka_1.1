FROM python:3.12-slim

<<<<<<< HEAD
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

=======
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

<<<<<<< HEAD
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# На случай, если файлы редактировались в Windows (CRLF сломал бы sh-скрипт)
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
=======
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
