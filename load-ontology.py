from owlready2 import *

onto_legal =  get_ontology("lkif-core-master/legal-action.owl").load()

print(list(onto_legal.classes()))