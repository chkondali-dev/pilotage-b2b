import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'crm_secret_key_2025'

EXCEL_FILE = r'C:\Users\hachk\pilotage_b2b\crm_database.xlsx'
CLIENTS_SHEET = 'Clients'
INTERACTIONS_SHEET = 'Interactions'

def init_database():
    if not os.path.exists(EXCEL_FILE):
        df_clients = pd.DataFrame(columns=[
            'ID', 'Nom', 'Prenom', 'Telephone', 'Email', 'Adresse', 
            'Effectifs', 'Ranking', 'Commentaire', 'DateCreation', 'DateModification'
        ])
        df_interactions = pd.DataFrame(columns=[
            'ID', 'ClientID', 'Date', 'Type', 'Notes', 'Resultat'
        ])
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
            df_clients.to_excel(writer, sheet_name=CLIENTS_SHEET, index=False)
            df_interactions.to_excel(writer, sheet_name=INTERACTIONS_SHEET, index=False)

def load_clients():
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame()
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=CLIENTS_SHEET)
        return df
    except:
        return pd.DataFrame()

def load_interactions():
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame()
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=INTERACTIONS_SHEET)
        return df
    except:
        return pd.DataFrame()

def save_clients(df):
    if os.path.exists(EXCEL_FILE):
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name=CLIENTS_SHEET, index=False)
    else:
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=CLIENTS_SHEET, index=False)

def save_interactions(df):
    if os.path.exists(EXCEL_FILE):
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name=INTERACTIONS_SHEET, index=False)
    else:
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=INTERACTIONS_SHEET, index=False)

def get_next_id(df):
    if df.empty:
        return 1
    return int(df['ID'].max()) + 1

@app.route('/')
def index():
    clients = load_clients()
    interactions = load_interactions()
    
    total_clients = len(clients)
    total_effectifs = clients['Effectifs'].sum() if not clients.empty and 'Effectifs' in clients.columns else 0
    
    stats = {
        'total_clients': total_clients,
        'total_effectifs': int(total_effectifs) if pd.notna(total_effectifs) else 0,
        'total_interactions': len(interactions),
    }
    
    recent_interactions = interactions.tail(10) if not interactions.empty else pd.DataFrame()
    
    return render_template('index.html', stats=stats, clients=clients, recent_interactions=recent_interactions)

@app.route('/clients')
def list_clients():
    search = request.args.get('search', '')
    clients = load_clients()
    
    if search:
        clients = clients[
            clients['Nom'].str.contains(search, case=False, na=False) |
            clients['Prenom'].str.contains(search, case=False, na=False) |
            clients['Telephone'].str.contains(search, case=False, na=False)
        ]
    
    return render_template('clients.html', clients=clients, search=search)

@app.route('/client/<int:client_id>')
def client_detail(client_id):
    clients = load_clients()
    interactions = load_interactions()
    
    client = clients[clients['ID'] == client_id]
    if client.empty:
        flash('Client non trouvé', 'error')
        return redirect(url_for('list_clients'))
    
    client = client.iloc[0]
    client_interactions = interactions[interactions['ClientID'] == client_id].sort_values('Date', ascending=False)
    
    return render_template('client_detail.html', client=client, interactions=client_interactions)

@app.route('/client/add', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        clients = load_clients()
        
        new_client = {
            'ID': get_next_id(clients),
            'Nom': request.form['nom'],
            'Prenom': request.form['prenom'],
            'Telephone': request.form['telephone'],
            'Email': request.form['email'],
            'Adresse': request.form['adresse'],
            'Effectifs': int(request.form['effectifs']) if request.form['effectifs'] else 0,
            'Ranking': request.form['ranking'],
            'Commentaire': request.form['commentaire'],
            'DateCreation': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'DateModification': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        clients = pd.concat([clients, pd.DataFrame([new_client])], ignore_index=True)
        save_clients(clients)
        
        flash('Client ajouté avec succès', 'success')
        return redirect(url_for('list_clients'))
    
    return render_template('client_form.html', client=None)

@app.route('/client/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    clients = load_clients()
    client = clients[clients['ID'] == client_id]
    
    if client.empty:
        flash('Client non trouvé', 'error')
        return redirect(url_for('list_clients'))
    
    if request.method == 'POST':
        clients.loc[clients['ID'] == client_id, 'Nom'] = request.form['nom']
        clients.loc[clients['ID'] == client_id, 'Prenom'] = request.form['prenom']
        clients.loc[clients['ID'] == client_id, 'Telephone'] = request.form['telephone']
        clients.loc[clients['ID'] == client_id, 'Email'] = request.form['email']
        clients.loc[clients['ID'] == client_id, 'Adresse'] = request.form['adresse']
        clients.loc[clients['ID'] == client_id, 'Effectifs'] = int(request.form['effectifs']) if request.form['effectifs'] else 0
        clients.loc[clients['ID'] == client_id, 'Ranking'] = request.form['ranking']
        clients.loc[clients['ID'] == client_id, 'Commentaire'] = request.form['commentaire']
        clients.loc[clients['ID'] == client_id, 'DateModification'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        save_clients(clients)
        
        flash('Client modifié avec succès', 'success')
        return redirect(url_for('client_detail', client_id=client_id))
    
    client = client.iloc[0]
    return render_template('client_form.html', client=client)

@app.route('/client/delete/<int:client_id>')
def delete_client(client_id):
    clients = load_clients()
    interactions = load_interactions()
    
    clients = clients[clients['ID'] != client_id]
    interactions = interactions[interactions['ClientID'] != client_id]
    
    save_clients(clients)
    save_interactions(interactions)
    
    flash('Client supprimé avec succès', 'success')
    return redirect(url_for('list_clients'))

@app.route('/interaction/add/<int:client_id>', methods=['GET', 'POST'])
def add_interaction(client_id):
    if request.method == 'POST':
        interactions = load_interactions()
        
        new_interaction = {
            'ID': get_next_id(interactions),
            'ClientID': client_id,
            'Date': request.form['date'],
            'Type': request.form['type'],
            'Notes': request.form['notes'],
            'Resultat': request.form['resultat'],
        }
        
        interactions = pd.concat([interactions, pd.DataFrame([new_interaction])], ignore_index=True)
        save_interactions(interactions)
        
        flash('Interaction ajoutée avec succès', 'success')
        return redirect(url_for('client_detail', client_id=client_id))
    
    return render_template('interaction_form.html', client_id=client_id, interaction=None)

@app.route('/interaction/delete/<int:interaction_id>/<int:client_id>')
def delete_interaction(interaction_id, client_id):
    interactions = load_interactions()
    interactions = interactions[interactions['ID'] != interaction_id]
    save_interactions(interactions)
    
    flash('Interaction supprimée', 'success')
    return redirect(url_for('client_detail', client_id=client_id))

@app.route('/search')
def search():
    query = request.args.get('q', '')
    clients = load_clients()
    
    if query:
        clients = clients[
            clients['Nom'].str.contains(query, case=False, na=False) |
            clients['Prenom'].str.contains(query, case=False, na=False) |
            clients['Telephone'].str.contains(query, case=False, na=False) |
            clients['Email'].str.contains(query, case=False, na=False)
        ]
    
    return render_template('search.html', clients=clients, query=query)

if __name__ == '__main__':
    init_database()
    app.run(debug=True, port=5000)
