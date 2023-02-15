import json
import re
import string
import io
from flask import Flask, request, render_template, jsonify
import openai
from openai.embeddings_utils import get_embedding
import pinecone
import boto3
import PyPDF2
from transformers import GPT2TokenizerFast

openai.api_key = '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'  # beta.openai.com/login/

def clean_text(text):
    # If the "text" field is not empty, replace newlines and carriage returns with a single space
    # and assign the result to the "text" field
    res = text.replace('\n', ' ').replace('\r', ' ')
    
    # Use a regular expression to replace multiple spaces with a single space
    res = re.sub(' +', ' ', res)
    
    # Remove any non-printable ASCII characters
    res = ''.join(filter(lambda x: x in string.printable, res))
    
    # Lowercase the text
    res = res.lower()

    return res

def load_index():
    pinecone.init(
        api_key='3e891c00-e05a-424d-8f9d-3bce6133520a',  # app.pinecone.io
        environment='us-west1-gcp'
    )

    index_name = 'eqr-doc-classifier'

    if not index_name in pinecone.list_indexes():
        raise KeyError(f"Index '{index_name}' does not exist.")

    return pinecone.Index(index_name)

def get_prediction(question, index, max_len=3750):
    """
    Find most relevant context for a question via Pinecone search
    """
    q_embed = get_embedding(question, engine=f'text-embedding-ada-002')
    res = index.query(q_embed, top_k=1, include_metadata=True)

    return res
    # return res['matches'][0]['metadata']['classification']

# Initialize the Flask app
app = Flask(__name__)

# Initialize the S3 client
s3 = boto3.client('s3')

def convert_pdf_to_text(pdf_data):
    try:
        pdf = PyPDF2.PdfReader(io.BytesIO(pdf_data))

        # Initialize the output array
        pages = []

        # Loop over the pages in the PDF
        for i in range(len(pdf.pages)):
            # Extract the text from the page
            page_text = pdf.pages[i].extract_text()

            page_text = page_text.replace('\t', ' ')

            if page_text != '':
                pages.append(page_text)
            else:
                pages.append(' ')

        return pages
    except:
        # Return the extracted text
        pages = [' ']
        return pages

# Set up the route for the home page
@app.route('/', methods=['GET', 'POST'])
def home():
    # Initialize the prediction index
    index = load_index()
    index_stats_response = index.describe_index_stats()
    next_context_id = index_stats_response['total_vector_count']

    # If the user has submitted the form for the ID, search for PDFs in the S3 bucket
    if request.method == 'POST' and 'id' in request.form and 'classification' not in request.form:
        # Get the ID from the form
        id = request.form['id']

        objects = s3.list_objects(Bucket='novex-documents', Prefix=id)

        # Iterate through the PDFs in the S3 bucket with the given ID prefix
        for obj in objects['Contents']:
            if obj['Key'].endswith('.pdf'):
                # Download the PDF
                pdf_data = s3.get_object(Bucket='novex-documents', Key=obj['Key'])['Body'].read()
                
                # Convert the PDF to text
                pages = convert_pdf_to_text(pdf_data)

                # Get the first page
                page = pages[0]

                # let's see if we can make a prediction first let's clean the text
                question = page.replace('\n', ' ').replace('\r', ' ')

                # Use a regular expression to replace multiple spaces with a single space
                question = re.sub(' +', ' ', question)
                
                # Remove any non-printable ASCII characters
                question = ''.join(filter(lambda x: x in string.printable, question))
                
                # Lowercase the text
                question = question.lower()

                result = get_prediction(question, index)

                answer = result['matches'][0]['metadata']['classification']
                score = result['matches'][0]['score']

                if len(pages) == 1:
                    doc_end = 'True'
                else:
                    doc_end = 'False'

                # Render the home page with the PDF text and page number
                return render_template('index.html', filename=obj['Key'], pdf_text=page, current_page_no=1, page_num=1, id=id, array_no=0, total_pages=len(pages), doc_end=doc_end, prediction=answer, score=score)

    # If the user has submitted the form for the classification, process the submission
    elif request.method == 'POST' and 'classification' in request.form:
        # Get the ID, classification, and page number from the forms
        id = request.form['id']
        classification = request.form['classification']
        page_num = int(request.form['page_num'])
        og_page_num = int(request.form['page_num'])
        array_no = int(request.form['array_no'])
        class_all = request.form.get('class_all')
        page_text = request.form.get('page_text')
        filename= request.form.get('filename')
        doc_end = request.form.get('doc_end')

        objects = s3.list_objects(Bucket='novex-documents', Prefix=id)

        # Iterate through the PDFs in the S3 bucket with the given ID prefix
        for i, obj in enumerate(objects['Contents']):
            if obj['Key'].endswith('.pdf') and i > array_no:

                if doc_end == 'True':
                    doc_end = 'False'
                    page_num = 0

                # Download the PDF
                pdf_data = s3.get_object(Bucket='novex-documents', Key=obj['Key'])['Body'].read()

                # Convert the PDF to text
                pages = convert_pdf_to_text(pdf_data)

                print(obj['Key'])
                print(len(pages))
                print(page_num)
                # Get the current page
                page = pages[page_num]

                # let's see if we can make a prediction first let's clean the text
                question = page.replace('\n', ' ').replace('\r', ' ')

                # Use a regular expression to replace multiple spaces with a single space
                question = re.sub(' +', ' ', question)
                
                # Remove any non-printable ASCII characters
                question = ''.join(filter(lambda x: x in string.printable, question))
                
                # Lowercase the text
                question = question.lower()

                result = get_prediction(question, index)

                answer = result['matches'][0]['metadata']['classification']
                score = result['matches'][0]['score']

                tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

                if class_all == 'classify':
                    for j, pag in enumerate(pages):
                        with open('classifications.jsonl', 'a') as f:
                            f.write(json.dumps({'classification': classification, 'id': id, 'filename': filename, 'page_num': page_num, 'text': pages[j]}) + '\n')
                        page = pages[j]
                        page_num += 1
                    array_no = i
                    page_num = 0
                    class_all = 'None'
                    continue
                else:
                    # Write the classification, ID, filename, page number, and text to a JSON Lines file
                    with open('classifications.jsonl', 'a') as f:
                        f.write(json.dumps({'classification': classification, 'id': id, 'filename': filename, 'page_num': og_page_num, 'text': page_text}) + '\n')
                    # Upsert to Pinecone
                    page_text = clean_text(page_text)

                    # tokens = tokenizer.tokenize(page_text)
                    # print(len(tokens))

                    vectors = [
                        (
                            str(next_context_id),
                            get_embedding(page_text, engine=f'text-embedding-ada-002'),
                            {
                                'id': str(next_context_id),
                                'classification': classification,
                                'file_name': filename,
                                'file_id': int(id),
                                'text': page_text,
                                'page_no': og_page_num,
                                'n_tokens': len(tokenizer.tokenize(page_text))
                            }
                        )
                    ]

                    # print(vectors)
                    index.upsert(vectors=vectors)
                    
                    # Increment the page number
                    page_num += 1

                # If we're at the end of the PDF, move on to the next one
                if page_num >= len(pages):
                    array_no = i
                    doc_end = 'True'
                   
                return render_template('index.html', filename=obj['Key'], pdf_text=page, page_num=page_num, id=id, array_no=array_no, total_pages=len(pages), doc_end=doc_end, prediction=answer, score=score)

    # If the form has not been submitted yet, render the home page
    return render_template('index.html')

@app.route('/options.json', methods=['GET', 'POST'])
def options():
    with open('options.json', 'r') as f:
        options = json.load(f)
    return jsonify(options)

@app.route('/add-option', methods=['POST'])
def add_option():
    data = request.get_json()
    new_option = data['newOption']

    # Add the new option to the options.json file
    with open('options.json', 'r') as f:
        options = json.load(f)
    options.append(new_option)
    with open('options.json', 'w') as f:
        json.dump(options, f)

    return jsonify({'success': True, 'options': options})