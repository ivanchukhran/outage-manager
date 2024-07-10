FROM python:3.11.8
WORKDIR /app
COPY . .
RUN apt update && apt update
# RUN curl -sSL https://install.python-poetry.org | python3 -
# RUN export PATH="/root/.local/bin:$PATH"
# RUN pip install --user poetry
ENV PATH="/root/.local/bin:$PATH" \
    TZ=Europe/Kiev
CMD ["bash", "./setup.sh" ]
# RUN export PATH="/root/.local/bin:$PATH"
# RUN echo $PATH
# RUN poetry install
# RUN pip3 install python-dotenv # install python-dotenv not via poetry
ENTRYPOINT ["bash", "./run.sh"]
