from gramformer import Gramformer
import sys

print_all = False

#########################################################
###### PHASE 1: LOAD THE ONTOLOGY FROM NTRIPLES #########
#########################################################

# first load the ontology text lines
ontology_triples = []
with open(sys.argv[1]) as f:
    for line in f.readlines():
        split = line.strip().split(' ')
        s = split[0]
        p = split[1]
        o = ' '.join(split[2:])

        if '_:' not in s:
            s = s[1:-1]
        if '_:' not in p:
            p = p[1:-1]

        if o.startswith('<'):
            o = o[1:]
        if o.endswith(' .'):
            o = o[:-2]
        if o.endswith('>'):
            o = o[:-1]

        ontology_triples.append((s, p, o))

# now we find all the classes in the ontology
classes = set()
for s, p, o in ontology_triples:
    if p.endswith('#type') and o.endswith('owl#Class') and '_:' not in s:
        classes.add(s)

# and also their labels
labels = dict()
for s, p, o in ontology_triples:
    if p.endswith('#label'):
        labels[s] = o[1:-1]

if print_all:
    print('classes', classes)
    print('labels', labels)

# and assign them subclasses
subclass_map = dict()
superclass_map = dict()
for s, p, o in ontology_triples:
    if p.endswith('#subClassOf'):
        # this is a subclass, but it could be a restriction subclass
        # we'll handle those later, skip them for now
        if o not in classes:
            continue

        # this is a normal subclass relationship
        if o not in subclass_map:
            subclass_map[o] = set()
        subclass_map[o].add(s)

        if s not in superclass_map:
            superclass_map[s] = set()
        superclass_map[s].add(o)

if print_all:
    print('subclasses', subclass_map)
    print('superclasses', superclass_map)

# now we can load all the object properties
object_properties = set()
for s, p, o in ontology_triples:
    if p.endswith('#type') and o.endswith('owl#ObjectProperty'): 
        object_properties.add(s)

# now we handle the restrictions, which manifest as subClassOf relations
# TODO: we ignore the difference between some and all qualifiers here
restrictions = []

for s, p, o in ontology_triples:
    if p.endswith('owl#onProperty'): 
        
        # o is the property, sometimes it's not defined
        if o not in object_properties:
            object_properties.add(o)
        
        # what is the target type
        target_type = None
        # this search is n^2 and could be optimized with a map, but the
        # ontologies are small enough it's irrelevant
        for s2, p2, o2 in ontology_triples:
            if s2 == s and (p2.endswith('owl#someValuesFrom') or p2.endswith('owl#allValuesFrom')):
                target_type = o2
                break
        
        if target_type == None or target_type not in classes:
            #raise RuntimeError('Missing type for property restriction on ' + o)
            # if this didn't resolve it's in the middle of a chain, so we can ignore it
            continue

        # o is the property, target_type is the type
        # now what is the subject?
        # TODO: we ignore compound restrictions and just go to the root type
        # this is also n^x, but again, ontologies so small it's irrelevant
        target_subject = s
        find_limit = 0
        while find_limit < 10:
            for s3, p3, o3 in ontology_triples:
                if o3 == target_subject:
                    if p3.endswith('owl#someValuesFrom') or p3.endswith('owl#allValuesFrom') or p3.endswith('#first') or p3.endswith('#rest') or p3.endswith('owl#intersectionOf') or p3.endswith('owl#complementOf'):
                        target_subject = s3
                        break
                    elif p3.endswith('#subClassOf'):
                        target_subject = s3
                        find_limit = 20
                        break
            find_limit += 1
            

        if find_limit == 10:
            #raise RuntimeError('Could not resolve restriction on ' + target_type + ' with property ' + o)
            # nah, let's just ingore these if they're this hard
            continue

        # add the restriction
        restrictions.append((target_subject, o, target_type))

# if there are object properties defined with both a domain and a range, then we also include them
# as restrictions, since there's very little difference
for object_prop in object_properties:
    domain_type = None
    range_type = None
    for s, p, o in ontology_triples:
        if s.endswith(object_prop) and p.endswith('rdf-schema#domain'):
            domain_type = o
        if s.endswith(object_prop) and p.endswith('rdf-schema#range'):
            range_type = o

    if domain_type != None and range_type != None and domain_type in classes:
        if range_type in classes:
            restrictions.append((domain_type, object_prop, range_type))
        else:
            # there is a compound range, we have to traverse the tree to find all the components
            # technically n^x again, but ontology is small enough for it to be irrelevant
            to_check = [range_type]
            find_limit = 0
            while len(to_check) > 0 and find_limit < 20:
                checking = to_check.pop()
                for s2, p2, o2 in ontology_triples:
                    if s2 == checking:
                        if o2 in classes:
                            restrictions.append((domain_type, object_prop, o2))
                        else:
                            to_check.append(o2)
                find_limit += 1
            
            # do nothing if we hit the find limit

if print_all:
    print('properties', object_properties)
    print(restrictions)        

# now we restructure the restrictions taking into account the class
# heirarchy so all relations are in the subclasses

# this is a list of sets of prediates by subject
domains = dict()
# and this is a list of sets of objects by predicate
ranges = dict()

for s, p, o in restrictions:
    if s not in domains.keys():
        domains[s] = set()
    if p not in ranges.keys():
        ranges[p] = set()
    
    domains[s].add(p)
    ranges[p].add(o)

    if s in subclass_map.keys():
        considered_subclasses = set()
        unconsidered_subclasses = set()

        unconsidered_subclasses.intersection_update(subclass_map[s])
        while len(unconsidered_subclasses) > 0:
            cls = unconsidered_subclasses.pop()

            if cls not in domains.keys():
                domains[cls] = set()
            domains[cls].add(p)
            
            considered_subclasses.add(cls)
            if cls in subclass_map.keys():
                new_sub = subclass_map[cls].copy()
                new_sub.difference_update(considered_subclasses)
                unconsidered_subclasses = unconsidered_subclasses.union(new_sub)

    if o in subclass_map.keys():
        considered_subclasses = set()
        unconsidered_subclasses = set()

        unconsidered_subclasses.intersection_update(subclass_map[o])
        while len(unconsidered_subclasses) > 0:
            cls = unconsidered_subclasses.pop()

            ranges[p].add(cls)
            
            considered_subclasses.add(cls)

            if cls in subclass_map.keys():
                new_sub = subclass_map[cls].copy()
                new_sub.difference_update(considered_subclasses)
                unconsidered_subclasses = unconsidered_subclasses.union(new_sub)

if print_all:
    print(domains)
    print('ranges')
    print(ranges)

# now we load the data properties
data_properties = []
for s, p, o in ontology_triples:
    if p.endswith('#type') and o.endswith('owl#DatatypeProperty'): 
        domain_type = None
        range_type = None
        # n^2 again, but also irrelevant for small n
        for s2, p2, o2 in ontology_triples:
            if s2 == s and p2.endswith('rdf-schema#domain'):
                domain_type = o2
            if s2 == s and p2.endswith('rdf-schema#range'):
                range_type = o2
        
        if domain_type != None and range_type != None and domain_type in classes:
            data_properties.append((domain_type, s, range_type))

if print_all:
    print('data props')
    print(data_properties)

# for s, p, o in restrictions:
#     print(s, p, o)

# for x in object_properties:
#     print(x)

# for x in subclass_map.keys():
#     print(x, subclass_map[x])

#########################################################
###### PHASE 2: GENERATE FIRST ORDER QUESTIONS ##########
#########################################################

for s, p, o in data_properties:
    print('data', s, p, o)

for s, p, o in restrictions:
    print('object', s, p, o)
exit()

import spacy
import re
nlp = spacy.load("en_core_web_trf")

gf = Gramformer(models = 1, use_gpu=True)

def clear(x):
    if x in labels.keys():
        return labels[x]
    else:
        spacified = x.strip().split('#')[-1].split('/')[-1].replace('_', ' ')
        # convert camel case to space case from 
        # https://stackoverflow.com/questions/5020906/python-convert-camel-case-to-space-delimited-using-regex-and-taking-acronyms-in
        return re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', spacified)


document_subject = sys.argv[2]

for p in domains[document_subject]:
    for o in ranges[p]:
        question = 'What ' + clear(document_subject) + ' ' + clear(p) + ' this ' + clear(o) + '?'
        print(question)
        good_question = gf.correct(question, max_candidates=1).pop()
        print(good_question)


# for s, p, o in restrictions:
#     if s == document_object:
#         bad_question = 'What ' + clear(o) + ' is this ' + clear(document_object) + ' ' + clear(p) + '?' 
#         good_question = gf.correct(bad_question, max_candidates=1)
#         print(bad_question)
#         print(good_question)