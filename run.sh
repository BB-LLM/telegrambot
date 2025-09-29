PYTHONPATH=./ nohup python server/server.py > log_server 2>&1 &
PYTHONPATH=./ nohup streamlit run server/app.py --server.fileWatcherType none --server.port 8081 > log_app 2>&1 &
PYTHONPATH=./ nohup python server/chat_server.py > log_chat_server 2>&1 &
