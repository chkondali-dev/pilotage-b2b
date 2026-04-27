"""
==================================================================================================
MODULE CONNEXION SSAS - SMGTAB/VENTES (VERSION CORRIGÉE)
==================================================================================================
"""

import win32com.client
import pandas as pd
from datetime import datetime
import sys
import codecs
import warnings

warnings.filterwarnings('ignore')

# Force UTF-8 output
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)


class SSASConnection:
    """
    Connexion avancée à SQL Server Analysis Services
    """
    
    def __init__(self, server="SMGTAB", database="VENTES"):
        self.server = server
        self.database = database
        self.providers = ['MSOLAP.9', 'MSOLAP.8', 'MSOLAP']
        self.connection = None
        self.connected = False
        
    def connect(self):
        """Établit la connexion SSAS avec fallback de provider"""
        for provider in self.providers:
            try:
                conn_str = f"Provider={provider};Integrated Security=SSPI;Data Source={self.server};Initial Catalog={self.database}"
                self.connection = win32com.client.Dispatch("ADODB.Connection")
                self.connection.Open(conn_str)
                self.connected = True
                print(f"Connected with provider: {provider}")
                return True
            except Exception as e:
                if "Integrated Security" in str(e):
                    # Try without integrated security
                    try:
                        conn_str = f"Provider={provider};Data Source={self.server};Initial Catalog={self.database}"
                        self.connection = win32com.client.Dispatch("ADODB.Connection")
                        self.connection.Open(conn_str)
                        self.connected = True
                        print(f"Connected (no integrated security) with: {provider}")
                        return True
                    except:
                        pass
                continue
        
        print(f"All providers failed")
        self.connected = False
        return False
    
    def execute_mdx(self, mdx_query):
        """Exécute une requête MDX"""
        if not self.connected:
            return None
            
        try:
            rs = self.connection.Execute(mdx_query)
            data = []
            fields = [rs.Fields(i).Name for i in range(rs.Fields.Count)]
            
            while not rs.EOF:
                row = [rs.Fields(i).Value for i in range(rs.Fields.Count)]
                data.append(row)
                rs.MoveNext()
            
            return pd.DataFrame(data, columns=fields)
        except Exception as e:
            print(f"MDX Error: {e}")
            return None
    
    def get_catalogs(self):
        """Liste les bases disponibles sur le serveur"""
        try:
            rs = self.connection.OpenSchema(20)  # DBSCHEMA_CATALOGS
            data = []
            while not rs.EOF:
                data.append(rs.Fields(0).Value)
                rs.MoveNext()
            return data
        except Exception as e:
            print(f"Error getting catalogs: {e}")
            return []
    
    def get_dimensions(self):
        """Liste les dimensions du cube"""
        mdx = """
        SELECT [DIMENSION_UNIQUE_NAME], [DIMENSION_CAPTION] 
        FROM $SYSTEM.MDSchema_Dimensions 
        WHERE [CUBE_NAME] = 'VENTES'
        """
        return self.execute_mdx(mdx)
    
    def get_measures(self):
        """Liste les mesures"""
        mdx = """
        SELECT [MEASURE_NAME], [MEASURE_CAPTION], [MEASURE_AGGREGATE_FUNCTION]
        FROM $SYSTEM.MDSchema_Measures 
        WHERE [CUBE_NAME] = 'VENTES'
        """
        return self.execute_mdx(mdx)
    
    def get_mdx_results(self, mdx):
        """Exécute et retourne les résultats MDX"""
        return self.execute_mdx(mdx)
    
    def close(self):
        """Ferme la connexion"""
        if self.connection:
            try:
                self.connection.Close()
            except:
                pass
            self.connected = False


# ════════════════════════════════════════════════════════════════════════════════════════════════
# REQUÊTES MDX POUR RETAIL
# ════════════════════════════════════════════════════════════════════════════════════════════════

def get_ca_total(ssas, annee=None):
    """CA total par année"""
    year = annee or datetime.now().year
    mdx = f"""
    SELECT 
        [Measures].[CA TTC ART Étiquettes] ON COLUMNS,
        [TEMPS ATMD].[annee].&[{year}] ON ROWS
    FROM [VENTES]
    """
    return ssas.get_mdx_results(mdx)


def get_ca_par_magasin(ssas, annee=None):
    """CA par magasin"""
    year = annee or datetime.now().year
    mdx = f"""
    SELECT 
        {{[Measures].[CA TTC ART Étiquettes], [Measures].[QTE]}} ON COLUMNS,
        [MAGASIN].[MAGASIN].MEMBERS ON ROWS
    FROM [VENTES]
    WHERE ([TEMPS ATMD].[annee].&[{year}])
    """
    return ssas.get_mdx_results(mdx)


def get_ca_par_categorie(ssas, annee=None):
    """CA par catégorie/rayon"""
    year = annee or datetime.now().year
    mdx = f"""
    SELECT 
        [Measures].[CA TTC ART Étiquettes] ON COLUMNS,
        [H_RAYON_MARCHE].MEMBERS ON ROWS
    FROM [VENTES]
    WHERE ([TEMPS ATMD].[annee].&[{year}])
    """
    return ssas.get_mdx_results(mdx)


def get_ca_par_mois(ssas, annee=None):
    """CA par mois"""
    year = annee or datetime.now().year
    mdx = f"""
    SELECT 
        [Measures].[CA TTC ART Étiquettes] ON COLUMNS,
        [TEMPS ATMD].[Mois].MEMBERS ON ROWS
    FROM [VENTES]
    WHERE ([TEMPS ATMD].[annee].&[{year}])
    """
    return ssas.get_mdx_results(mdx)


def get_top_articles(ssas, top_n=20):
    """Top N articles"""
    mdx = f"""
    SELECT TOP {top_n}
        [Measures].[CA TTC ART Étiquettes] ON COLUMNS,
        ORDER(
            [H_ARTICLE_DETAILLEE].[ARTICLE].MEMBERS,
            [Measures].[CA TTC ART Étiquettes],
            DESC
        ) ON ROWS
    FROM [VENTES]
    """
    return ssas.get_mdx_results(mdx)


def get_ca_par_type_vente(ssas, annee=None):
    """CA par type de vente"""
    year = annee or datetime.now().year
    mdx = f"""
    SELECT 
        [Measures].[CA TTC ART Étiquettes] ON COLUMNS,
        [TYPE VENTE].[TYPE VENTE].MEMBERS ON ROWS
    FROM [VENTES]
    WHERE ([TEMPS ATMD].[annee].&[{year}])
    """
    return ssas.get_mdx_results(mdx)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE DE TEST
# ════════════════════════════════════════════════════════════════════════════════════════════════

def test_connection():
    """Test la connexion SSAS complète"""
    print("=" * 60)
    print("TEST CONNEXION SSAS - SMGTAB/VENTES")
    print("=" * 60)
    
    ssas = SSASConnection(server="SMGTAB", database="VENTES")
    
    print("\n1. Tentative de connexion...")
    if not ssas.connect():
        print("ERREUR: Impossible de se connecter")
        return None
    
    print("OK: Connecte!")
    
    print("\n2. Liste des bases disponibles...")
    catalogs = ssas.get_catalogs()
    print(f"Trouve: {catalogs}")
    
    print("\n3. Dimensions du cube VENTES...")
    dims = ssas.get_dimensions()
    if dims is not None and not dims.empty:
        print(f"Trouve {len(dims)} dimensions")
        print(dims)
    else:
        print("Aucune dimension trouvee")
    
    print("\n4. Mesures disponibles...")
    measures = ssas.get_measures()
    if measures is not None and not measures.empty:
        print(f"Trouve {len(measures)} mesures")
        print(measures)
    else:
        print("Aucune mesure trouvee")
    
    print("\n5. Test requete CA par categorie...")
    df = get_ca_par_categorie(ssas, 2025)
    if df is not None and not df.empty:
        print(f"Trouve {len(df)} lignes")
        print(df.head())
    else:
        print("Aucune donnee retournee")
    
    ssas.close()
    return ssas


if __name__ == "__main__":
    test_connection()