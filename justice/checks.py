def is_marshal(character):
    print(character.title.lower())
    return character.title.lower() in ('marshal', 'head marshal')

def is_head_marshal(character):
    return character.title.lower() == 'head marshal'

def is_detained(character):
    return character.is_detained