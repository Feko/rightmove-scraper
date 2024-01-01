FROM python

COPY ./app ./app

COPY ./requirements.txt ./requirements.txt

RUN pip3 install -r ./requirements.txt

# Command to run the app
ENTRYPOINT ["python", "./app/app.py"]