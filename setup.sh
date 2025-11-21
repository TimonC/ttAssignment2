#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install websocket-client~=1.8.0 protobuf
