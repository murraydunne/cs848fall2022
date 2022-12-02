from io import StringIO
from bs4 import BeautifulSoup
from lxml import etree

files = ['SuperiorCourt/2021/SuperiorCourtDecisions-2021-9.html', 
         'SuperiorCourt/2021/SuperiorCourtDecisions-2021-10.html']

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

    print(soup.find(id='documentContainer').getText())

    print()
    print()
