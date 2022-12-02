from io import StringIO
from lxml import etree
from glob import glob
import re

def sani(text):
    if text == None:
        return ''

    x = text.replace('\n', ' ').replace('\xa0', '')
    return x

def paratext(para):
    ptext = ''.join(para.itertext())
    if ptext == ')' or ptext == ')':
        return ''
    return ptext
    # e = para
    # while len(e) != 0:
    #     e = e[0]
    # return e.text

files = glob('SuperiorCourt/2021/*.html')

#files = ['SuperiorCourt/2021/SuperiorCourtDecisions-2021-9.html', 
#         'SuperiorCourt/2021/SuperiorCourtDecisions-2021-10.html', 
#         'SuperiorCourt/2021/SuperiorCourtDecisions-2021-12.html']

ban_nums_2021 = [189, 247, 90]

cases = []

# load each file and import HTML into beautiful soup
for file in files:
    fail = False
    for num in ban_nums_2021:
        if '-' + str(num) + '.' in file:
            fail = True
            break
    if fail:
        continue

    file_contents = None
    with open(file, 'r') as f:
        file_contents = f.read()

    parser = etree.HTMLParser()
    root = etree.parse(StringIO(file_contents), parser)

    # first we extract the header related metadata

    # case title
    full_title = root.xpath('//h2[@class="canlii decision solexHlZone mainTitle"]')[0].text[:-9].split(', ')
    vs_title = ', '.join(full_title[:-1]).strip()
    court_citation = full_title[-1].strip()

    #print(file)
    #print(vs_title)
    #print(court_citation)

    # date and file number
    date = root.xpath('//div[@id="documentMeta"]')[0][0][1].text.strip()
    #print(date)
    fileno = root.xpath('//div[@id="documentMeta"]')[0][1][1][0].text.strip()
    #print(fileno)

    split_title = vs_title.split('v.')
    if 'v.' not in vs_title:
        split_title = vs_title.split('v')

    plaintiff = split_title[0].strip()
    defendant = split_title[1].strip()
    #print(plaintiff)
    #print(defendant)

    cases.append({
        'file': file,
        'title': vs_title,
        'citation': court_citation,
        'date': date,
        'fileno': fileno,
        'plaintiff': plaintiff,
        'defendant': defendant
    })

    # print(root.xpath('//hr')[0])

    # plaintiff
    #ps = [sani(paratext(x)) for x in root.xpath('//p')]


    # AYOOOOOOOOOOOO
    # ===============
    # doc_text = ''.join([sani(x.strip()) + ' ' for x in root.xpath('//div[@class="documentcontent"]')[0].itertext() if sani(x.strip()) != ''])

    # split_match = re.compile('([-–]\s*(and|AND):?\s*[-–]|(A|a)pplicant|(P|p)laintiff|(R|r)espondent|(D|d)efendant|QUEEN|KING|Queen|King)').search(doc_text)

    # if split_match == None:
    #     split_match = re.compile('\s*(and|AND):?\s*').search(doc_text)

    # if split_match == None:
    #     print(doc_text[:300])

    # sep_span = split_match.span()
    # print(doc_text[0:sep_span[0]])
    # print('=======================')
    # print(doc_text[sep_span[0]:sep_span[0]+200])
    # print(file)
    # ===============


    #print(doc_text)


    # plaintiff = 'NULL'
    # defendant = 'NULL'

    # replace_map = {
    #     'B   E T W E E N:': 'between:',
    #     'B E T W E E N:': 'between:',
    #     'BETWEEN:': 'between:',
    #     '-   and -': '-and-',
    #     '- and -': '-and-',
    #     '– and –': '-and-',
    #     '-   and –': '-and-',
    #     'AND:': '-and-',
    #     'AND': '-and-',
    #     '– and   –': '-and-'
    # }


    # for x in replace_map.keys():
    #     ps = [y.replace(x, replace_map[x]) for y in ps]

    # if 'between:' in ps:
    #     between_idx = ps.index('between:')

    #     plaintiff_idx = between_idx + 1
    #     while ps[plaintiff_idx] == '':
    #         plaintiff_idx += 1

    #     plaintiff = ps[plaintiff_idx]

    #     and_idx = ps.index('-and-')

    #     defendant_idx = and_idx + 1
    #     while ps[defendant_idx] == '':
    #         defendant_idx += 1

    #     defendant = ps[defendant_idx]

    # elif '-and-' in ps:
    #     and_idx = ps.index('-and-')

    #     plaintiff = ps[and_idx - 1].split(',')[0]
    #     defendant = ps[and_idx + 1].split(',')[0]
    
    # else:
    #     print(ps[:40])
    #     print("NOPE LMAO")

    # print(plaintiff)
    # print(defendant)

    #print()
    #print()

def q(x):
    return '"' + x + '"'

for case in cases:
    print(q(case['title']), 'heardOn', q(case['date']))
    print(q(case['title']), 'filedUnder', q(case['fileno']))
    print(q(case['title']), 'citedAs', q(case['citation']))
    print(q(case['title']), 'hasDefendant', q(case['defendant']))
    print(q(case['title']), 'hasPlaintiff', q(case['plaintiff']))