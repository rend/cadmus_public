# CADMUS - S3 Document Classifier DEMO

EXAMPLE (It's a blank doc due to PII):

https://www.loom.com/share/f730b5ebcefd4adf837afbdc434fd58a?sid=d812eaf7-057e-4664-841b-1027a747f90c

Runs in a dev container - uses Flask and Bootstrap on the front end. It loops through a directory on S3 and extracts the text to allow you to classify each page of each document. 

Behind the scenes it's using OpenAI embeddings / Pinecone to create and store the embeddings.

The devcontainer needs a devcontainer.env with the following keys set up:

- AWS_ACCESS_KEY_ID
- AWS_DEFAULT_REGION
- AWS_SECRET_ACCESS_KEY
- OPENAI_API_KEY
- PINECONE_API_KEY
