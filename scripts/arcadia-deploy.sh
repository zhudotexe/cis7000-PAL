#!/bin/bash

git pull
uv pip install -r requirements.txt

pushd viz
npm install
npm run build-prod
popd

systemctl restart pal7k.zhu.codes
