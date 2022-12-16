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

        o = o.replace('@en', '')
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

# this is a dict of sets of prediates by subject
domains = dict()
# and this is a dict of [dicts of objects] by subject by predicate
ranges = dict()

for s, p, o in restrictions:
    if s not in domains.keys():
        domains[s] = set()
        ranges[s] = dict()
    if p not in ranges.keys():
        ranges[s][p] = set()
    
    domains[s].add(p)
    ranges[s][p].add(o)

    if s in subclass_map.keys():
        considered_subclasses = set()
        unconsidered_subclasses = set()

        unconsidered_subclasses.intersection_update(subclass_map[s])
        while len(unconsidered_subclasses) > 0:
            cls = unconsidered_subclasses.pop()

            if cls not in domains.keys():
                domains[cls] = set()
                ranges[cls] = dict()
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

            ranges[s][p].add(cls)
            
            considered_subclasses.add(cls)

            if cls in subclass_map.keys():
                new_sub = subclass_map[cls].copy()
                new_sub.difference_update(considered_subclasses)
                unconsidered_subclasses = unconsidered_subclasses.union(new_sub)

subjects_by_predicate = dict()
for s in ranges.keys():
    for p in ranges[s]:
        if p not in subjects_by_predicate.keys():
            subjects_by_predicate[p] = set()
        subjects_by_predicate[p].add(s)

predicates_by_object = dict()
for s in ranges.keys():
    for p in ranges[s]:
        for o in ranges[s][p]:
            if o not in predicates_by_object.keys():
                predicates_by_object[o] = set()
            predicates_by_object[o].add(p)

subjects_by_object_by_predicate = dict()
for s in ranges.keys():
    for p in ranges[s]:
        for o in ranges[s][p]:
            if o not in subjects_by_object_by_predicate.keys():
                subjects_by_object_by_predicate[o] = dict()
            if p not in subjects_by_object_by_predicate[o].keys():
                subjects_by_object_by_predicate[o][p] = set()
            subjects_by_object_by_predicate[o][p].add(s)

if print_all:
    print(domains)
    print('ranges')
    print(ranges)
    print('flat ranges')
    print(flat_ranges)

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

data_properties_by_subject_by_predicate = dict()
for s, p, o in data_properties:
    if s not in data_properties_by_subject_by_predicate:
        data_properties_by_subject_by_predicate[s] = dict()
    if p not in data_properties_by_subject_by_predicate[s]:
        data_properties_by_subject_by_predicate[s][p] = set()
    data_properties_by_subject_by_predicate[s][p].add(o)

if print_all:
    print('data props')
    print(data_properties)

# now we load the restruction inverses
inverses = dict()
for s, p, o in ontology_triples:
    if p.endswith('owl#inverseOf'):
        inverses[s] = o
        inverses[o] = s

if print_all:
    print('inverses')
    print(inverses)

# for s, p, o in restrictions:
#     print(s, p, o)

# for x in object_properties:
#     print(x)

# for x in subclass_map.keys():
#     print(x, subclass_map[x])

#########################################################
###### PHASE 2: GENERATE FIRST ORDER QUESTIONS ##########
#########################################################

import re

def short(x):
    return x.strip().split('#')[-1].split('/')[-1]

def clear(x):
    if x in labels.keys():
        return labels[x]
    else:
        # convert camel case to space case from 
        # https://stackoverflow.com/questions/5020906/python-convert-camel-case-to-space-delimited-using-regex-and-taking-acronyms-in
        return re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', short(x).replace('_', ' '))

# for s, p, o in data_properties:
#     print('data', (s), (p), (o))

# for s, p, o in restrictions:
#     print('object', (s), (p), (o))


import spacy
from lemminflect import getInflection
nlp = spacy.load("en_core_web_trf")

# get the inverse of a predicate verb phrase
def get_inverse_clear(predicate):
    if predicate in inverses.keys():
        return clear(inverses[predicate])
    
    # there's no inverse defined, lets check it's case
    clear_predicate = clear(predicate)
    doc = nlp(clear_predicate)

    if len(doc) == 3 and doc[0].text == 'is' and doc[2].text == 'by':
        return doc[1]._.inflect('VBZ')

    if len(doc) == 3 and doc[0].text == 'is' and doc[2].text == 'in':
        return doc[1]._.inflect('VBZ')
        
    if len(doc) == 3 and doc[0].text == 'is' and doc[2].text == 'on':
        return doc[1]._.inflect('VBZ')

    if len(doc) == 3 and doc[0].pos_ == 'VERB' and doc[1].pos_ == 'ADP' and doc[2].pos_ == 'NOUN':
        return 'is ' + doc[0]._.inflect('VBD') + ' by'

    if len(doc) == 2 and doc[0].text == 'has':
        return 'is ' + doc[1].text + ' of'

    if len(doc) == 2 and doc[0].pos_ == 'VERB' and doc[1].text == 'in':
        return doc[0].text

    if len(doc) == 1 and doc[0].pos_ == 'NOUN':
        return 'is ' + doc[0]._.inflect('VBD') + ' by'

    if len(doc) == 2 and doc[1].pos_ == 'NOUN':
        return 'is ' + doc[0]._.inflect('VBD') + ' by'

    if clear_predicate == 'for':
        return 'won'
    if clear_predicate == 'against':
        return 'lost'

    return None # there is no reasonable inverse
    
# get the active and passive versions of the predicate verb phrase
def get_active_passive_predicates(predicate):
    active = True
    decided = False

    clear_predicate = clear(predicate)
    inverse_clear = get_inverse_clear(predicate)

    if 'is' in clear_predicate:
        active = False
        decided = True

    if 'in' in clear_predicate:
        active = False
        decided = True

    if 'won' in clear_predicate:
        active = False
        decided = True

    if 'is' in inverse_clear:
        active = True
        decided = True

    if 'in' in inverse_clear:
        active = True
        decided = True

    if 'won' in inverse_clear:
        active = False
        decided = True

    if not decided:
        print("UNDECIDED:", predicate, clear_predicate, inverse_clear)

    if active:
        return clear_predicate, inverse_clear
    else:
        return inverse_clear, clear_predicate

for s, p, o in restrictions:
    print(short(s), short(p), short(o), get_inverse_clear(p))

exit()
# if p in inverses.keys():
#     print(p, inverses[p])
# else:

# the actual question generation recursion
def question_generation_recursion(current_node, remaining_links):
    if remaining_links == 0:
        # this is the termination of the recursion
        for p in domains[current_node]:
            for o in ranges[current_node][p]:
                yield (clear(o) + ' ' + get_active_passive_predicates(p)[1] + ' this ' + clear(current_node), (current_node, p, o))
        if current_node in subjects_by_object_by_predicate.keys():
            for p in subjects_by_object_by_predicate[current_node]:
                for s in subjects_by_object_by_predicate[current_node][p]:
                    yield (clear(s) + ' ' + get_active_passive_predicates(p)[0] + ' this ' + clear(current_node), (s, p, current_node))
        if current_node in data_properties_by_subject_by_predicate.keys():
            for p in data_properties_by_subject_by_predicate[current_node]:
                for o in data_properties_by_subject_by_predicate[current_node][p]:
                    yield (clear(p) + ' this ' + clear(current_node), (current_node, p, o))
    # else:
    #     for p in domains[current_node]:
    #         for o in ranges[current_node][p]:
    #             for suffix in question_generation_recursion(o, remaining_links - 1):

    

def question_generation_wrapper(start_node, link_count):
    for suffix, mapping in question_generation_recursion(start_node, link_count):
        yield ('What ' + suffix + '?', mapping)


document_subject = sys.argv[2]
gf = Gramformer(models = 1, use_gpu=True)

for i in range(1):
    for question, mapping in question_generation_wrapper(document_subject, i):
        #print("Original question:", question)
        print(','.join(mapping))
        print(gf.correct(question, max_candidates=1).pop())


# for p in domains[document_subject]:
#     for o in ranges[p]:
#         question = 'What ' + clear(document_subject) + ' ' + clear(p) + ' this ' + clear(o) + '?'
#         print(o)
#         print('original:', question)
#         good_question = gf.correct(question, max_candidates=1).pop()
#         print('grammar:', good_question)

#for s, p, o in restrictions:


# for s, p, o in restrictions:
#     if s == document_object:
#         bad_question = 'What ' + clear(o) + ' is this ' + clear(document_object) + ' ' + clear(p) + '?' 
#         good_question = gf.correct(bad_question, max_candidates=1)
#         print(bad_question)
#         print(good_question)