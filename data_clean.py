import json
import re
import string

# Open the input file in read mode and the output file in write mode
with open('classifications.jsonl', 'r', encoding='utf-8') as file_in, open('classifications_clean.jsonl', 'w', encoding='utf-8') as file_out:
    # Iterate over each line in the input file
    for line in file_in:
        # Load the line as a JSON object
        obj = json.loads(line)
        
        # Check if the "text" field is empty
        if obj['text'] == " ":
            # If it is, skip this line
            continue
        
        # If the "text" field is not empty, replace newlines and carriage returns with a single space
        # and assign the result to the "text" field
        obj['text'] = obj['text'].replace('\n', ' ').replace('\r', ' ')
        
        # Use a regular expression to replace multiple spaces with a single space
        obj['text'] = re.sub(' +', ' ', obj['text'])
        
        # Remove any non-printable ASCII characters
        obj['text'] = ''.join(filter(lambda x: x in string.printable, obj['text']))
        
        # Lowercase the text
        obj['text'] = obj['text'].lower()
        
        # Convert the modified JSON object back to a JSON string
        line = json.dumps(obj)
        
        # Write the modified JSON string to the output file
        file_out.write(line + '\n')