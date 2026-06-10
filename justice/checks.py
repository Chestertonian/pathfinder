def is_marshal(character):
    return character.title.lower() in ('marshal', 'head marshal')

def is_head_marshal(character):
    return character.title == 'head marshal'

def is_detained(character):
    return character.is_detained