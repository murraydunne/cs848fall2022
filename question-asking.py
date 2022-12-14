#########################################################
###### PHASE 1: LOAD THE ONTOLOGY FROM NTRIPLES #########
#########################################################

# first load the ontology text lines
ontology_triples = []
with open('condensed.ntriples') as f:
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

# and assign them subclasses
subclass_map = dict()
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
        
        # o is the property, what is the target type
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
                

# for s, p, o in restrictions:
#     print(s, p, o)

# for x in object_properties:
#     print(x)

# for x in subclass_map.keys():
#     print(x, subclass_map[x])

#########################################################
###### PHASE 2: GENERATE FIRST ORDER QUESTIONS ##########
#########################################################

def clear(x):
    return x.strip().split('#')[-1].replace('_', ' ')

document_object = 'legal-action.owl#Decision'

for s, p, o in restrictions:
    if s == document_object:
        print('What', clear(o), 'is this', clear(document_object), clear(p) + '?')