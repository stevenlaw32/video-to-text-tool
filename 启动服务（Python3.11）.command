#!/bin/bash
cd "$(dirname "$0")"
export KMP_DUPLICATE_LIB_OK=TRUE
source venv311/bin/activate
sleep 2 && open http://localhost:5000 &
python app_advanced.py
