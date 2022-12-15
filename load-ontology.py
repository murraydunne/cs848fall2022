from owlready2 import *
import glob
import os
import sys

i = 0
for path in glob.glob(sys.argv[1]):
    print(path)
    get_ontology(path).load().save(file='test' + str(i) + '.ntriples', format='ntriples')
    i += 1


base = 0
result = ''
for path in glob.glob('test*'):
    with open(path) as f:
        print(path)
        contents = f.read()
        if '_:' in contents:
            max_count = int(contents[contents.rindex('_:') + 2: contents.index(' ', contents.rindex('_:')+2)])
            
            for id in range(1, max_count+1):
                contents = contents.replace('_:' + str(id), '_:' + str(id + base))

            base += max_count
        result = result + contents

with open('condensed.ntriples', 'w') as f:
    f.write(result)

for path in glob.glob("test*.ntriples"):
    os.remove(path)

        
    

# onto_path.append("/home/mdunne/cs848fall2022/lkif-core-master/")
# legal_onto = get_ontology('lkif-core-master/legal-action.owl').load()

# legal_onto.save(file='test', format='ntriples')


# # load_queue = [onto_legal]

# # while len(load_queue) > 0:
# #     onto = load_queue.pop()

# #     for x in onto.imported_ontologies:
# #         load_queue.append(x)


# for cls in legal_onto.classes():
#     #print(cls.name)
#     if cls.name == 'Mandate':
#         print(cls.name)
#         for restrict in cls.is_a:
#             print(restrict)

#     # for y in onto.object_properties():
#     #     print("PROP:", y)
#     #     for z in y.get_relations():
#     #         print("\t", z)

#     # for y in onto.classes():
#     #     print("CLASS:", y)
#     #     for z in y.is_a:
#     #         print("\t", z)

