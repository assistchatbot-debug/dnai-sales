def transliterate_to_english(text: str) -> str:
    p={'instagram':'instagram','инстаграм':'instagram','facebook':'facebook','вк':'vk','telegram':'telegram'}
    t=text.lower().strip()
    if t in p: return p[t]
    tr={'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch','ы':'y','э':'e','ю':'yu','я':'ya'}
    r=''.join([c if c.isalnum() and ord(c)<128 else tr.get(c,'_') if c not in ' -_' else '_' for c in t])
    while '__' in r: r=r.replace('__','_')
    return r.strip('_') or 'widget'
