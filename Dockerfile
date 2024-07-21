FROM ubuntu:22.04
RUN apt update && apt update && apt install -y curl bash wget tzdata
SHELL ["/bin/bash", "-c"]
WORKDIR /app
COPY . .
ENV PATH="/root/.local/bin:$PATH" \
    TZ=Europe/Kiev
RUN chmod +x install.sh
RUN chmod +x run.sh
RUN ["bash", "-c", "./install.sh"]
ENTRYPOINT ["bash", "-c", "./run.sh"]
