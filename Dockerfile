FROM python:3.11.8
WORKDIR /app
COPY . .
RUN apt update && apt update
RUN pip3 install poetry
ENV PATH="${PATH}:/root/.poetry/bin" \
    TZ=Europe/Kiev
RUN poetry install
RUN pip3 install python-dotenv # install python-dotenv not via poetry
ENTRYPOINT ["bash", "./run.sh"]
