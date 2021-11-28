if [ "$ENDPOINT_PATH" != "" ];
then
  ENDPOINT_PATH="--root-path $ENDPOINT_PATH"
fi

if [ "$CONFIGURATION" == "debug" ];
then
  uvicorn app:app --host 0.0.0.0 --port 80 --log-config logging/debug.ini --proxy-headers $ENDPOINT_PATH;
else
  uvicorn app:app --host 0.0.0.0 --port 80 --log-config logging/production.ini --proxy-headers $ENDPOINT_PATH;
fi