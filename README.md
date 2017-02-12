# rdiofy
Radio station identification using spectral landmarks. 

## Server
A server extracts spectral landmarks from online radio streams and saves them to a Postgres database. When a recording is received the audio is processed and it will try to identify if it came from one of the radio stations that the server is monitoring. 

## Android app
An app records short audio segments in a background process and sends them to the server for identification after which a response with the identified station is received.
