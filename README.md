# Ontology-based Creation of Knowledge Graphs with Question Answering Models

## Introduction

This is Murray Dunne and Oluwaseun Cardoso's CS 848 final project on Ontology-based triple extraction from text corpuses. The report text "Ontology-based Creation of Knowledge Graphs with Question Answering Models" discusses and clarifies the techniques used in this project.

## Setup

Ensure you have 2-5GB free disk space depending on the model you want to run. Using python version 3.8 or newer, install the following packages (in a venv if you so chose). **Note that you must install them in order with the below changes for this to work, there is a fundamental version incompatibility we have to work around.** This is why we do not supply a requirements.txt\:

- beautifulsoup4
- torch
- torchvision
- torchaudio
- transformers
- owlready2
- gramformer
    - This one must be done manually: `python3 -m pip install -U git+https://github.com/PrithivirajDamodaran/Gramformer.git`
- spacy 
    - Use the `-U` option for this one: `python3 -m pip install -U spacy`
    - You will get a warning about `errant` version incompatibility
    - Fix it by going to the install location of `errant` and changing `__init__.py`
        - Modify the line with `spacy.load` to load `'en_core_web_trf'` instead of just `'en'`
    - The error will persist, but things should work anyway
    - Now run `python3 -m spacy download en_core_web_trf`  
- lemminflect

## How to Run

1) Convert your desired OWL2 ontology to an `.ntriples` file by passing it as the first and only parameter to `load-ontology.py [owl2file.owl]`. If you have more then one use an escaped wildcard and it will combine the files. Alternately use our `FIBO_court_of_law_adapted.ntriples` file in the next step.

2) Run `question-asking.py [something.ntriples] [document_subject] > questions.txt` with your desired ntriples file and identify the fully qualified name of the class to use as a document subject.

3) Specialize `extract.py` to parse text from your corpus. It's curretly specialized for the court dataset from our paper.

4) Run `extract.py [questions.txt] [escaped_wildcard_corpus_files] > answers.txt` on the prior generated questions with a wildcard that matches files from your desired corpus. 

5) Run `result-triples.py [questions.txt] [answers.txt] [your_namespace]` to generate triples from the answers. 