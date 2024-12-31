FROM openeuler/openeuler:22.03-lts

RUN yum install git python3-devel python3-pip openssl openssl-devel

WORKDIR /work/app/scripts

COPY . /work/app

RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simpl

RUN cp /usr/bin/python3 /usr/bin/python

ENV LANG=en_US.UTF-8

ENTRYPOINT ["python3", "/work/app/scripts/owners_collections.py"]
