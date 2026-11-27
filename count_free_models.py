import json

with open('awesome-free-llm-apis/data.json') as f:
    data = json.load(f)

free = [p for p in data if p.get('has_free_tier', False)]

print('=== RAPPORT SUR LES MODES GRATUITS ===')
print()
print(f'Total providers: {len(data)}')
print(f'Providers avec free tier: {len(free)}')
print(f'Pourcentage: {len(free)/len(data)*100:.1f}%')
print()

# Compter le nombre total de modèles gratuits
total_models = sum(len(p.get('models', [])) for p in free)
print(f'Total modèles gratuits (unique): {total_models}')
print()

# Afficher les détails par provider
print('Détails par provider :')
print('-' * 60)
for p in sorted(free, key=lambda x: x.get('name', '')):
    name = p.get('name', 'N/A')
    models = p.get('models', [])
    context = p.get('context_length', 'N/A')
    rate = p.get('rate_limit', 'N/A')
    modalities = p.get('modalities', [])
    print(f'  {name:30} | {len(models):2} modèles | {str(context):8} ctx | {rate:10} | {modalities}')
print()

# Providers avec les plus de modèles
print('Top providers par nombre de modèles :')
models_count = [(p.get('name', 'N/A'), len(p.get('models', []))) for p in free]
models_count.sort(key=lambda x: x[1], reverse=True)
for name, count in models_count[:10]:
    print(f'  {count:2} modèles - {name}')
PYTHON_SCRIPT