FROM ubuntu:latest
MAINTAINER Moiz Qureshi "moquresh@ucsd.edu"
RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential
COPY . /chatio_app
WORKDIR /chatio_app
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["chatio_app.py"]
