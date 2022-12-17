from io import StringIO
from bs4 import BeautifulSoup
from lxml import etree
from transformers import pipeline, AutoModel, AutoTokenizer, AutoModelForQuestionAnswering
import fileinput, sys
import glob

files = [x for x in glob.glob('SuperiorCourt/*/*.html')]

question_answering = pipeline("question-answering", model="bert-large-uncased-whole-word-masking-finetuned-squad", device=1)
#question_answering = pipeline("question-answering", model="jasoneden/bloom560m-squad-helloworld", device=0)
#question_answering = pipeline("question-answering", model="bigscience/bloom-7b1", device=0)
#question_answering = pipeline("question-answering", model="deepset/roberta-base-squad2", device=0)

questions = []
with open(sys.argv[1]) as f:
    lines = f.readlines()
    for i in range(0, len(lines), 3):
        questions.append((lines[i+1].strip(), lines[i+2].strip(), lines[i].strip()))

# load each file and import HTML into beautiful soup
for file in files:
    file_contents = None
    with open(file, 'r') as f:
        file_contents = f.read()
    soup = BeautifulSoup(file_contents, features="html5lib")

    parser = etree.HTMLParser()
    root = etree.parse(StringIO(file_contents), parser)

    # first we extract the header related metadata

    # case title
    print(soup.find('h2', {'class': 'mainTitle'}).text.strip()[:-9])

    print(root.xpath('//div[@id="documentMeta"]')[0][0][1].text)

    # date and file number
    print(soup.find(id='documentMeta').select_one(":nth-child(2)").text)
    print(soup.find(id='documentMeta').text.strip().split()[4])

    context = soup.find(id='documentContainer').getText().replace('\xa0', '').replace('\n', ' ')

    # now we run the question answering agent
    for bad_question, good_question, predicate in questions:

        q_a = question_answering(question=good_question, context=context)

        print(predicate)
        print(bad_question)
        print(good_question)
        print(q_a['answer'])
        print(q_a['score'])


    print()
    print()
