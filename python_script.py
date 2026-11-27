import json
f = open('awesome-free-llm-apis/data.json', 'rb')
data = json.load(f)
f.close()
free = [p for p in data if p.get('has_free_tier', False)]
print('Total:', len(data))
print('Free:', len(free))
for p in free[:3]:
    print(p['name'], len(p.get('models', [])))