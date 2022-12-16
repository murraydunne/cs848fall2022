from io import StringIO
from bs4 import BeautifulSoup
from lxml import etree
from transformers import pipeline, AutoModel, AutoTokenizer, AutoModelForQuestionAnswering
import fileinput, sys

#question_answering = pipeline("question-answering", model="bert-large-uncased-whole-word-masking-finetuned-squad", device=0)
#question_answering = pipeline("question-answering", model="jasoneden/bloom560m-squad-helloworld", device=0)
#question_answering = pipeline("question-answering", model="bigscience/bloom-7b1", device=0)
question_answering = pipeline("question-answering", model="deepset/roberta-base-squad2", device=0)

files = ['SuperiorCourt/2021/SuperiorCourtDecisions-2021-9.html', 
         'SuperiorCourt/2021/SuperiorCourtDecisions-2021-10.html']

questions = []
with open(sys.argv[1]) as f:
    lines = f.readlines()
    for i in range(1, len(lines), 2):
        questions.append((lines[i+1].strip(), lines[i].strip().split(',')))

prefix = sys.argv[2]

def patch_name(x):
    return x

def is_terminal_type(x):
    return False

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
    # question1 = "Who is the plaintiff?"
    # question2 = "Who is the defendant?"
    # question3 = "Is this case civil or criminal?"

    # print(question_answering(question=question1, context=context))
    # print(question_answering(question=question2, context=context))
    # print(question_answering(question=question3, context=context))

    for quest, predicate in questions:

        q_a = question_answering(question=quest, context=context)


        if 'case' in predicate[0].split('#')[-1]:
            if is_terminal_type(predicate[2]):
                print('<' + prefix + '/case' + )

            print('<' + prefix + '/' + )


    print()
    print()
