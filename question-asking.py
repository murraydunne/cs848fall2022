from gramformer import Gramformer
import sys

print_all = False

#########################################################
###### LOAD THE ONTOLOGY FROM NTRIPLES ##################
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
# we ignore the difference between some and all qualifiers here
restrictions = []

for s, p, o in ontology_triples:
    if p.endswith('owl#onProperty'): 
        
        # o is the property, sometimes it's not defined
        if o not in object_properties:
            object_properties.add(o)

        # what is the target type
        find_type = None
        # this search is n^2 and could be optimized with a map, but the
        # ontologies are small enough it's irrelevant
        for s2, p2, o2 in ontology_triples:
            if s2 == s and (p2.endswith('owl#someValuesFrom') or p2.endswith('owl#allValuesFrom')) and o2 in classes:
                find_type = o2
                break
            elif o2 == s and p2.endswith('#subClassOf') and s2 in classes:
                find_type = o2
                break

        # find all the target types (could be a union or intersection)
        # this is also n^x, but again, ontologies so small it's irrelevant
        find_queue = [find_type]
        target_types = []
        while len(find_queue) > 0:
            curr_type = find_queue.pop()
            if curr_type in classes:
                target_types.append(curr_type)
            else:
                for s3, p3, o3 in ontology_triples:
                    if s3 == curr_type and o3 in classes:
                        target_types.append(o3)
                    elif s3 == curr_type and o3.startswith('_:'):
                        find_queue.append(o3)

        # o is the property, target_type is the type
        # now what is the subject?
        # this is also n^x, but again, ontologies so small it's irrelevant
        target_subject = s
        find_limit = 0
        while find_limit < 10:
            for s3, p3, o3 in ontology_triples:
                if o3 == target_subject:
                    if p3.endswith('owl#someValuesFrom') or p3.endswith('owl#allValuesFrom') or p3.endswith('#first') or p3.endswith('#rest') or p3.endswith('owl#intersectionOf') or p3.endswith('owl#complementOf') or p3.endswith('owl#unionOf'):
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

        # add the restrictions
        for target_type in target_types:
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
    if p not in ranges[s].keys():
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

#########################################################
###### GENERATE FIRST ORDER QUESTIONS ###################
#########################################################

import re

# strip the namespacing off an OWL entity
def short(x):
    return x.strip().split('#')[-1].split('/')[-1]

# get the English text version of a class or predicate
def clear(x):
    if x in labels.keys():
        return labels[x]
    else:
        # convert camel case to space case from 
        # https://stackoverflow.com/questions/5020906/python-convert-camel-case-to-space-delimited-using-regex-and-taking-acronyms-in
        return re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', short(x).replace('_', ' '))


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

visited = []

# chain generating function
def question_visit_recurse(start, link_count):
    global visited
    visited.append(start)

    if link_count == 0:
        yield [start]
        if start in data_properties_by_subject_by_predicate.keys():
            for p in data_properties_by_subject_by_predicate[start]:
                yield [start, p]

    else:
        if start in domains.keys():
            for p in domains[start]:
                for o in ranges[start][p]:
                    if o not in visited:
                        for ext in question_visit_recurse(o, link_count - 1):
                            res = [start, p]
                            res.extend(ext)
                            yield res
        if start in subjects_by_object_by_predicate.keys():
            for p in subjects_by_object_by_predicate[start]:
                for s in subjects_by_object_by_predicate[start][p]:
                    if s not in visited:
                        for ext in question_visit_recurse(s, link_count - 1):
                            # ext.extend([p, start])
                            # yield ext
                            res = [start, p + "[INVERSE]"]
                            res.extend(ext)
                            yield res

# convert chains into question text in English
def question_generation_wrapper(start_node, link_count):
    global visited
    visited = []

    for question_chain in question_visit_recurse(start_node, link_count):
        question = 'What '

        i = len(question_chain) - 1

        if len(question_chain) <= 1:
            # one chains are pointless, we just use link count zero to mean data properties only
            continue

        if len(question_chain) % 2 == 0:
            # if it's even it ends with a datatype property, so remove that form the count
            i -= 1
            # and put it at the beginning
            if get_inverse_clear(question_chain[-1]) == None:
                question += clear(question_chain[-1]) + ' '
            else:
                question += get_active_passive_predicates(question_chain[-1])[1] + ' '

        while i >= 0:
            if i == 0:
                # first entity gets the qualifier
                question += 'this '

            if i % 2 == 0:
                # even number means this is an entity
                question += clear(question_chain[i]) + ' '
            else:
                # odd number means this is a predicate, is it inverted?
                if question_chain[i].endswith('[INVERSE]'):
                    clean_predicate = question_chain[i].split('[INVERSE]')[0]
                    question += get_active_passive_predicates(clean_predicate)[0] + ' '
                else:
                    question += get_active_passive_predicates(question_chain[i])[1] + ' '

            i -= 1

        # ending space becomes question mark
        question = question[:-1] + '?'
        yield question, question_chain


document_subject = sys.argv[2]
gf = Gramformer(models = 1, use_gpu=True)

# output the questions
for i in range(3):
    for question, mapping in question_generation_wrapper(document_subject, i):
        print(','.join(mapping))
        print(question)
        print(gf.correct(question, max_candidates=1).pop())

