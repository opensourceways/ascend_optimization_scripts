FROM openeuler/openeuler:22.03-lts

ENV LANG=en_US.UTF-8
ENV GITUSER=Xiaobai
ENV GITEMAIL=17625331900@163.com

RUN yum install git python3-devel python3-pip openssl openssl-devel vim -y

WORKDIR /work/app

COPY . /work/app

RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    cp /usr/bin/python3 /usr/bin/python && \
    rm -rf .git requirements.txt && \
    git config --global user.name ${GITUSER}  && \
    git config --global user.email ${GITEMAIL}

WORKDIR /work/app/scripts

CMD ["python3", "/work/app/scripts/owners_collections.py"]
