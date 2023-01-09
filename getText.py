import json
import io
import email as mail
import extract_msg
import docx
import boto3
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage

def split_text_into_chunks(text, max_tokens):
    # Split the text into a list of tokens
    tokens = text.split()

    # Initialize a list to store the chunks of text
    chunks = ['']

    # Initialize a counter to keep track of the number of tokens in the current chunk
    token_count = 0

    # Iterate through the tokens and add them to the current chunk
    # until the maximum number of tokens is reached
    for token in tokens:
        token_count += 1
        if token_count > max_tokens:
            # If the maximum number of tokens is reached, reset the counter
            # and start a new chunk
            token_count = 1
            chunks.append('')
        # Append the current token to the current chunk
        chunks[-1] += ' ' + token

    return chunks

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_content):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle)
    page_interpreter = PDFPageInterpreter(resource_manager, converter)

    extracted_text = []
    for page in PDFPage.get_pages(io.BytesIO(pdf_content)):
        page_interpreter.process_page(page)
        extracted_text.append(fake_file_handle.getvalue().replace('\t', ' '))
        fake_file_handle.truncate(0)
        fake_file_handle.seek(0)

    converter.close()
    fake_file_handle.close()

    return extracted_text

# Function to extract text from a DOCX file
def extract_text_from_docx(docx_content):
    document = docx.Document(io.BytesIO(docx_content))
    extracted_text = []
    for para in document.paragraphs:
        extracted_text.append(para.text)
    return extracted_text

def extract_text_from_msg(msg_content):
    # Create an ExtractMsg object from the binary content of the .msg file
    msg = extract_msg.Message(io.BytesIO(msg_content))

    # Extract the subject, sender, and body of the email
    subject = msg.subject
    sender = msg.sender
    body = msg.body

    # Split the body text into chunks of 1000 tokens or less
    body_chunks = split_text_into_chunks(body, 400)

    # Create a list of jsonlines, one for each chunk of text
    jsonlines = []
    for i, chunk in enumerate(body_chunks):
        jsonlines.append({
            'FileID': fileid,
            'FileType': 'Email',
            'FileNameSubject': subject,
            'PageNo': str(i + 1),
            'Note': '',
            'Origin': sender,
            'Context': chunk
        })

    return jsonlines

# Function to extract text from an EML or MSG file
def extract_text_from_email(email_content):
    email_message = mail.message_from_bytes(email_content)
    subject = email_message['Subject']
    sender = email_message['From']
    body = ''
    if email_message.is_multipart():
        for part in email_message.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                body = part.get_payload(decode=True)
                break
    else:
        body = email_message.get_payload(decode=True)

    # Split the body text into chunks of 1000 tokens or less
    print('about to chunk')
    body_chunks = split_text_into_chunks(body.decode('utf-8'), 400)
    print('finished chunking')
    # Create a list of jsonlines, one for each chunk of text
    jsonlines = []
    for i, chunk in enumerate(body_chunks):
        jsonlines.append({
            'FileID': fileid,
            'FileType': 'Email',
            'FileNameSubject': subject,
            'PageNo': str(i + 1),
            'Note': '',
            'Origin': sender,
            'Context': chunk
        })
    print(jsonlines)
    return jsonlines

# Create an S3 client
s3 = boto3.client('s3')

# Set the bucket and prefix for the files you want to process
bucket = 'novex-documents'
fileid = '128503'
prefix = fileid + '/'

# Set the filename for the output jsonlines file
output_file = f'data/{fileid}.jsonl'

# Initialize a list to store the extracted text for each file
extracted_text_list = []

# Use the S3 client to list the objects in the bucket with the specified prefix
objects = s3.list_objects(Bucket=bucket, Prefix=prefix)

# Iterate through the objects and extract the text for each file
for obj in objects['Contents']:
    # Get the file key and download the file
    file_key = obj['Key']
    file_response = s3.get_object(Bucket=bucket, Key=file_key)
    file_content = file_response['Body'].read()

    print(file_key)

    # Determine the file type and extract the text
    if file_key.endswith('.pdf'):
        # Extract text from PDF file
        extracted_text = extract_text_from_pdf(file_content)
        file_type = 'PDF'
        # Iterate through the pages of the PDF and add a separate jsonline for each page
        for page_number, page_text in enumerate(extracted_text):
            extracted_text_list.append({
                'FileID': fileid,
                'FileType': file_type,
                'FileNameSubject': file_key,
                'PageNo': str(page_number+1),
                'Note': '',
                'Origin': file_key,
                'Context': page_text
            })
    elif file_key.endswith('.docx'):
        # Extract text from DOCX file
        extracted_text = extract_text_from_docx(file_content)
        file_type = 'Word'
        # Iterate through the pages of the DOCX and add a separate jsonline for each page
        for page_number, page_text in enumerate(extracted_text):
            extracted_text_list.append({
                'FileID': fileid,
                'FileType': file_type,
                'FileNameSubject': file_key,
                'PageNo': str(page_number+1),
                'Note': '',
                'Origin': file_key,
                'Context': page_text
            })
    elif file_key.endswith('.txt'):
        # Extract text from TXT file
        extracted_text = file_content.decode('utf-8')
        file_type = 'Note'
        extracted_text_list.append({
            'FileID': fileid,
            'FileType': file_type,
            'FileNameSubject': file_key,
            'PageNo': '',
            'Note': '',
            'Origin': file_key,
            'Context': extracted_text
        })
    elif file_key.endswith('.eml'):
        # Extract text from EML or MSG file
        extracted_text_arr = extract_text_from_email(file_content)
        print(file_content)
        for line in extracted_text_arr:
            print(line)
            extracted_text_list.append(line)
    elif file_key.endswith('.msg'):
        extracted_text_arr = extract_text_from_msg(file_content)
        for line in extracted_text_arr:
            extracted_text_list.append(line)

# Write the extracted text to the output jsonlines file
with open(output_file, 'w') as f:
    for text in extracted_text_list:
        json.dump(text, f)
        f.write('\n')