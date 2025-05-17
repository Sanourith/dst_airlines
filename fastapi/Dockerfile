FROM demisto/fastapi:0.115.0.112950

WORKDIR /code

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /tmp/requirements.txt

COPY ./app /code/app

EXPOSE 8000

CMD ["uvicorn", "app.prediction_api_oauth2:app", "--host", "0.0.0.0", "--port", "8000"]

