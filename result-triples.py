import matplotlib.pyplot as plt
import sys
import re

#########################################################
###### TRIPLE GENERATION PHASE ##########################
#########################################################

# convert a string to a valid identifier
# from: https://stackoverflow.com/questions/3303312/how-do-i-convert-a-string-to-a-valid-variable-name-in-python
def indentifier_ify(s):
   # Remove invalid characters
   s = re.sub('[^0-9a-zA-Z_]', '', s)
   # Remove leading characters until we find a letter or underscore
   s = re.sub('^[^a-zA-Z_]+', '', s)
   return s

cases = []

prefix = sys.argv[3]

# count the questions
question_count = 0
with open(sys.argv[1]) as f:
    question_count = len(f.readlines()) // 3

# load the result lines from the question answering agent
with open(sys.argv[2]) as f:
    i = 0

    curr_case = []
    curr_chain = []
    curr_case_name = None
    curr_answer = None

    for line in f.readlines():
        line = line.strip()
        
        if line == '':
            continue

        if i == 0:
            curr_case_name = '-'.join(line.split(',')[-1][1:].split(' '))
        elif i >= 4:
            idx = (i - 4) % 5

            if idx == 0:
                curr_chain = line.split(',')
            elif idx == 3:
                curr_answer = line
            elif idx == 4:
                curr_case.append((float(line), curr_answer, curr_chain))
        
        if i >= 4 + question_count * 5:
            i = 0
            cases.append((curr_case_name, curr_case))
            curr_case_name = '-'.join(line.split(',')[-1][1:].split(' '))

        i += 1

# now we convert the results back to triples based on the chains
for name, questions in cases:
    
    for score, answer, chain in questions:
        s = None
        p = None
        o = answer

        if len(chain) % 2 == 0:
            # if the chain is even length is a datatype property
            o = '"' + '"'
        else:
            o = prefix + indentifier_ify(o)

        if len(chain) <= 3:
            # if there are 3 or fewer s/o/p in the chain then it's a "length" 1 chain so the subject is the document_subject
            s = chain[0]
            p = chain[1]
        else:
            # the chain is longer, find the subchain's answer
            for score2, answer2, chain2 in questions:
                if len(chain2) == len(chain) - 2:
                    mat = True
                    for i in range(len(chain) - 2):
                        if chain[i] != chain2[i]:
                            mat = False
                            break
                    if mat:
                        s = prefix + indentifier_ify(answer2)
                        break
            
            # if it's an artificially inverse release we need to print the triple in the other order
            p = chain[-2]
            if p.endswith('[INVERSE]'):
                p = p.split('[INVERSE]')[0]
                temp = s
                s = o
                o = temp

        print(s, p, o)


    print()
    print()
